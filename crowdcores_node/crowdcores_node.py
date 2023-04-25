import asyncio
import websockets
import time
import json
import torch
from transformers import pipeline
import sys
import os
import gc
import psutil

#polyfills for earlier  versions of python
try:
    asyncio.create_task
except AttributeError:
    def asyncio_create_task(coro, *, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        return loop.create_task(coro)
else:
    asyncio_create_task = asyncio.create_task

try:
    asyncio.run
except AttributeError:
    def asyncio_run(coroutine, debug=False):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()
else:
    asyncio_run = asyncio.run


model_names=[];
model_pipelines={};
in_memory_models=[];

if torch.cuda.is_available():
    device_id=0;
else:
    device_id=-1;


async def run_async(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, func, *args, **kwargs)
    return result

def do_clear_all_models_in_memory(websockets,message):
    try:
        global model_pipelines;
        global in_memory_models;
        print("Clearing in memory models.");
        in_memory_models=[]
        del model_pipelines
        gc.collect()
        model_pipelines={}
        return {"success":1};
    except Exception as e:
        print(e)
        response={
            "success":0,
            "exception_name":e.__class__.__name__,
            "exception_message":str(e)
        }
        return response



def do_load_model_into_memory(websocket,message):
    try:
        global model_pipelines;
        global in_memory_models;

        request_data = message['pipeline_data']
        init_args=request_data["init_args"];
        init_kwargs=request_data["init_kwargs"];
        task=init_args[0];
        model_name=init_kwargs['model']
        model_task_name=model_name+"_"+task;
        if model_task_name in model_pipelines:
            print("Already Loaded")
        else:
            print("Loading model into memory...")
            model_pipelines[model_task_name] = pipeline(task,model=model_name,device=device_id)
            in_memory_models.append(model_task_name)
            print("Done Loading")
        response={
            "success":1,
        }
        return response;
    except Exception as e:
        print(e)
        response={
            "success":0,
            "exception_name":e.__class__.__name__,
            "exception_message":str(e)
        }
        return response



def do_process_pipeline_request(websocket,message):
    print("processing");
    try:
        global model_pipelines;
        global in_memory_models;
        request_data = message['pipeline_data']
        args=request_data["args"];
        kwargs=request_data["kwargs"];
        init_args=request_data["init_args"];
        init_kwargs=request_data["init_kwargs"];
        task=init_args[0];
        model_name=init_kwargs['model']
        #model_pipeline = pipeline(*init_args,**init_kwargs)
        print("Processing pipeline request:",task,"-",model_name)
        model_task_name=model_name+"_"+task;
        if model_task_name in model_pipelines:
            print("Processing from loaded memory model")
        else:
            model_pipelines[model_task_name] = pipeline(task,model=model_name,device=device_id)
            in_memory_models.append(model_task_name)
        r=model_pipelines[model_task_name](*args,**kwargs)
        response={
            "success":1,
            "pipeline_response_result":r
        }
        print("Completed pipeline request:",task,"-",model_name)
        return response;
    except Exception as e:
        response={
            "success":0,
            "exception_name":e.__class__.__name__,
            "exception_message":str(e)
        }
        return response


async def process_pipeline_request(websocket,message):
    #response = await run_async(do_process_pipeline_request,websocket,message)
    response =  do_process_pipeline_request(websocket,message)
    data = {'command': 'completed_pipeline_request','pipeline_response':response,'pipeline_request':message}
    await websocket.send(json.dumps(data))


async def load_model_into_memory(websocket,message):
    response =  do_load_model_into_memory(websocket,message)
    data = {'command': 'completed_load_model_into_memory','response':response,'request':message}
    await websocket.send(json.dumps(data))

async def clear_all_models_in_memory(websocket,message):
    response = do_clear_all_models_in_memory(websocket,message)
    data = {'command': 'completed_clear_all_models_in_memory','response':response,'request':message}
    await websocket.send(json.dumps(data))




async def init_load_models(websocket):
    await run_async(download_models,websocket)
    print("Models Download Complete")
    data = {'command': 'completed_models_download'}
    await websocket.send(json.dumps(data))

def download_models(websocket):
    for model_name, model_data in model_names.items():
        print("Loading Model:",model_name);
        try:
            pipeline(model=model_name,task=model_data['pipeline_tag'])
        except Exception as e:
            print(repr(e))
            print('Model could not load, skipping download...')


def get_free_ram():
    return psutil.virtual_memory().available;

def get_total_ram():
    return psutil.virtual_memory().total;

def get_free_disk_space():
    return psutil.disk_usage('/').free;

def get_total_disk_space():
    return psutil.disk_usage('/').total;

def get_gpu_memory():
    mem_stats = torch.cuda.memory_stats()
    return mem_stats;


    #free_mem = mem_stats['free_bytes']
    #total_mem = mem_stats['total_bytes']

async def receive_loop(websocket):
    while True:
        message = await websocket.recv()
        message_json = json.loads(message)

        if message_json['command'] == 'ping':


            data = {
                'command': 'pong',
                'in_memory_models':in_memory_models,
                'free_ram':get_free_ram(),
                'total_ram':get_total_ram(),
                'free_disk_space':get_free_disk_space(),
                'total_disk_space':get_total_disk_space(),
                'device_id':device_id,
                'free_gpu_memory':0,
                'total_gpu_memory':0
            }
            if device_id == 0:
                mem_stats=get_gpu_memory();
                data['free_gpu_memory']=mem_stats['free_bytes'];
                data['free_gpu_memory']=mem_stats['total_bytes'];

            await websocket.send(json.dumps(data))

        if message_json['command'] == 'got_models_names_list':
            global model_names
            model_names=message_json['model_names_list']
            asyncio_create_task(init_load_models(websocket))

        if message_json['command'] == 'process_pipeline_request':
            asyncio_create_task(process_pipeline_request(websocket,message_json))

        if message_json['command'] == 'load_model_into_memory':
            asyncio_create_task(load_model_into_memory(websocket,message_json))

        if message_json['command'] == 'clear_all_models_in_memory':
            asyncio_create_task(clear_all_models_in_memory(websocket,message_json))




async def send_loop(websocket):
    while True:
        #print("sending");
        await asyncio.sleep(15)
        data = {'command': 'ping'}
        await websocket.send(json.dumps(data))

async def start_node(websocket):
        data = {
            'command': 'node_started',
            'free_ram':get_free_ram(),
            'free_disk_space':get_free_disk_space(),
            'in_memory_models':in_memory_models,
            'free_ram':get_free_ram(),
            'total_ram':get_total_ram(),
            'free_disk_space':get_free_disk_space(),
            'total_disk_space':get_total_disk_space(),
            'device_id':device_id,
            'free_gpu_memory':0,
            'total_gpu_memory':0
        }
        if device_id == 0:
            mem_stats=get_gpu_memory();
            data['free_gpu_memory']=mem_stats['free_bytes'];
            data['total_gpu_memory']=mem_stats['total_bytes'];

        API_KEY = os.getenv('CROWDCORES_API_KEY');
        if API_KEY:
            data['api_key']=API_KEY;
        await websocket.send(json.dumps(data))


async def client():
    while True:
        try:
            async with websockets.connect("ws://ws.crowdcores.com") as websocket:
                consumer_task=asyncio_create_task(receive_loop(websocket))
                producer_task=asyncio_create_task(send_loop(websocket))
                asyncio_create_task(start_node(websocket))

                done, pending = await asyncio.wait(
                    [consumer_task,producer_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                #await asyncio.Future()
        #except (OSError, websockets.exceptions.ConnectionClosed) as e:
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)



def main():
    asyncio_run(client())

if __name__ == "__main__":
    main()

