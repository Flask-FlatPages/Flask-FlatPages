import yaml

# check that the dependency is installed
assert yaml.safe_load('- 42') == [42]
