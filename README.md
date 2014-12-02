# PyCache

A simple HTTP cache implemented using Twisted. Currently supports
- cache-control headers: max-age and no-store
- cache expiration clean up on interval

### Usage

Update the values in ```config.py``` and ```python run.py```.

### Development

```sh
# Set up environment
pip install -r requirements.txt -r dev-requirements.txt
# Run the tests
./run_tests.sh
```
