from setuptools import setup, find_packages

setup(
    name='crowdcores_node',
    version='1.0.2',
    packages=find_packages(),
    install_requires=[
        'websockets',
        'torch',
        'transformers'
    ],
    entry_points={
        'console_scripts': [
            'ccnode = crowdcores_node.node:main'
        ]
    }
)
