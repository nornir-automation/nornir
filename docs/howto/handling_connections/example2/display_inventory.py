from IPython.display import display, Markdown

HOSTS_FILE = "handling_connections/example2/inventory/hosts.yaml"

with open(HOSTS_FILE) as f:
    display(Markdown(f"```yaml\n{f.read()}\n```"))
