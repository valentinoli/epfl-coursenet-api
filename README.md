Set up virtual environment:
```bash
python -m venv ./py/env
```

```bash
pip install wheel setuptools
```

Activate virtual environment (Windows):
```bash
.\py\env\Scripts\activate
```

Install dependencies (when virtualenv is activated)
```bash
pip install -r requirements.txt
```

Install package in site-packages directory:
Note: This happens automatically when above line is run and ./py is in requirements.txt
```bash
python setup.py install --user
```

Run local redis server after installing it to your system
```bash
redis-server
```

Run redis server and Node app in parallel
```bash
npm run dev
```

Run the following in your activated environment to connect the environment to Jupyter notebook:
```bash
pip install --user ipykernel
python -m ipykernel install --user --name=coursebook-env
```
