import rdetoolkit

from modules_saxs import datasets_process

rdetoolkit.workflows.run(custom_dataset_function=datasets_process.dataset)
