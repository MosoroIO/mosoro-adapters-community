# Template Adapter

This is a template for creating new robot adapters. Copy this directory and customize.

## Steps

1. Copy this directory: `cp -r _template/ your_vendor/`
2. Rename `template_adapter.py` to `your_vendor_adapter.py`
3. Implement all methods in the adapter class
4. Update `template.yaml` with your vendor's connection details
5. Add tests in `tests/test_your_vendor.py`
