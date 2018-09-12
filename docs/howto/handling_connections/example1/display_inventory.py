from IPython.display import display, Markdown
from nornir.core import InitNornir

CONFIG_FILE = "handling_connections/example1/config.yaml"
HOSTS_FILE = "handling_connections/example1/inventory/hosts.yaml"

InitNornir(config_file="handling_connections/example1/config.yaml")

with open(HOSTS_FILE) as f:
    display(Markdown(f"```yaml\n{f.read()}\n```"))
