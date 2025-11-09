from setuptools import setup, find_packages

setup(
    name='scatools',
    version='0.1.1',
    packages=['scatools'],
    # required packages:
    # from scipy.stats import norm
    # import numpy as np
    # import time
    # import chipwhisperer as cw
    # import matplotlib.pyplot as plt
    # import plotly.graph_objects as go
    # import plotly.io as pio
    # import plotly.express as px
    # import pandas as pd
    # import subprocess
    install_requires=[
        'scipy',
        'numpy',
        'chipwhisperer',
        'matplotlib',
        'plotly',
        'pandas',
        'tqdm',
        'pyvcd',
        'scalib'
    ],
    description='A collection of tools for side-channel analysis',
    url='hegz.io',
    author='Hegz',
    author_email='y@hegz.io',
    license='MIT',)
