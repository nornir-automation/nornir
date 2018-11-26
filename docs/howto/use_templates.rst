Use templates
===========================
Templates are used to consistently generate configurations to hosts. while allow to  pass variables to the templates from the
inventory or from the python code.

Nornir use Jinja2 templates in order to populate the templates with variables, create some programming logic in the
templates and more, to fully understand Jinja2 templates engine:

http://jinja.pocoo.org/

Nornir has two methods to load templates:

* From file
* From string

Loading from file
===========================
Here is an example of how to load a template from file, the template is in /home/nornir/dns.j2::

    system {
     name-server {
            {{ host.data.name_server1 }};
            {{ host.data.name_server2 }};
        }
    }

Loading the templates using nornir::

    from nornir.plugins.tasks import networking, text

    def configure_dns(task):
        r = task.run(task=text.template_file,
                    name="Load template DNS",
                    template="dns.j2",
                    path="/home/nornir/",
                    **kwargs)
        task.host["config"] = r.result

        task.run(task=networking.napalm_configure,
             name="Loading DNS configuration to the devices",
             replace=False,
             configuration=task.host["config"])


Now let's pass a var not from the inventory:

the template is in /home/nornir/ntp.j2::

    system {
         ntp {
            server 0.ubuntu.pool.ntp.org ;
            server 1.ubuntu.pool.ntp.org ;
            source-address {{ ntp_source }}
        }
    }

Loading the templates using nornir::

    from nornir.plugins.tasks import networking, text

    def configure_dns(task, ntp_source):
        r = task.run(task=text.template_file,
                    name="Load template NTP",
                    template="ntp.j2",
                    path="/home/nornir/",
                    ntp_source=ntp_source,
                    **kwargs)
        task.host["config"] = r.result

        task.run(task=networking.napalm_configure,
             name="Loading NTP configuration to the devices",
             replace=False,
             configuration=task.host["config"])


Pay attention that we load the template we pass ``ntp_source=ntp_source``

Loading from string
===========================

Sometime it is better to load the template outside of nornir and pass it has a string to nornir, a use case might be
is that nornir use multi-thread and for each thread nornir will open the template file which is inefficient.
So we can pass to nornir the template as string

The template will be the same as before::

    system {
     name-server {
            {{ host.data.name_server1 }};
            {{ host.data.name_server2 }};
        }
    }


Loading the templates using nornir::

    from nornir.core import InitNornir
    from nornir.plugins.tasks import networking, text

    def configure_dns(task, template_dns):
        r = task.run(task=text.template_text,
                    name="Load template DNS",
                    template=template_dns,
                    **kwargs)
        task.host["config"] = r.result

        task.run(task=networking.napalm_configure,
             name="Loading DNS configuration to the devices",
             replace=False,
             configuration=task.host["config"])

    with open("/home/nornir/dns.j2") as f:
        dns = f.read()

    nr = InitNornir(config_file="config.yaml", dry_run=True)
    cmh = nr.filter(site="cmh", type="network_device")
    result = cmh.run(task=configure_dns, template_dns=dns)

Jinja2 has a concept of extending a template, extending a template allow us to create a base template which is common
to many hosts types and add some configuration that only used for some hosts types, the problem that when we use text
templates task Python doesn't now from where the template was loaded (The same applies to include, and other Jinja2 methods pointing to other templates).
In order to solve it we can pass the path to the
directory where base template. Example:

Base template::

    system {
         ntp {
            server 0.ubuntu.pool.ntp.org ;
            server 1.ubuntu.pool.ntp.org ;
            source-address {{ ntp_source }}
        }
    }
    {% block body %}
    {% endblock %}

The block tells Jinja2 where to add the additional text.
Our extended template name will be srx.j2::

    {% extends "route_ntp.j2" %}
    {% block body %}
    routing-options {
        static {
            route 0.ubuntu.pool.ntp.org next-hop {{ host.oob_default_gateway }};
            route 1.ubuntu.pool.ntp.org  next-hop {{ host.oob_default_gateway }};
    }
    {% endblock %}

The body block tells Jinja2 to take the text inside the block and add to the base template
Keep in mind that body is just a name and we can have more than one block name inside the template

So now our code::

    from nornir.core import InitNornir
    from nornir.plugins.tasks import networking, text

    def configure_ntp(task, template_ntp, template_route_ntp):
        if task.host.data.route_ntp:
            r = task.run(task=text.template_text,
                        name="Load template NTP with route",
                        template=template_route_ntp,
                        path="/home/nornir/"
                        **kwargs)
        else:
            r = task.run(task=text.template_text,
                        name="Load template NTP",
                        template=template_ntp,
                        **kwargs)
        task.host["config"] = r.result

        task.run(task=networking.napalm_configure,
             name="Loading NTP configuration to the devices",
             replace=False,
             configuration=task.host["config"])

    with open("/home/nornir/ntp.j2") as f:
        ntp = f.read()
    with open("/home/nornir/route_ntp.j2") as f:
        route_ntp = f.read()

    nr = InitNornir(config_file="config.yaml", dry_run=True)
    cmh = nr.filter(site="cmh", type="network_device")
    result = cmh.run(task=configure_ntp, template_ntp=ntp, template_route_ntp=route_ntp)

