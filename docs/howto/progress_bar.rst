Adding a progress bar
=====================

In this how to we want to show an example on how to integrate ``nornir`` with `tqdm <https://tqdm.github.io/>`_ to add a nice way of tracking progress of our script without having to print the results on screen. First, this is how the result will look like when we run the script:

.. image:: progress_bar/demo.gif

And now the code::

   from nornir import InitNornir
   from nornir_napalm.tasks import napalm_get

   from tqdm import tqdm

   nr = InitNornir(config_file="config.yaml")


   def multiple_progress_bar(task, napalm_get_bar, other_bar):
       """
       This task takes two paramters that are in fact bars;
       napalm_get_bar and other_bar. When we want to tell
       to each respective bar that we are done and should update
       the progress we can do so with bar_name.update()
       """
       task.run(task=napalm_get, getters=["facts"])
       napalm_get_bar.update()
       tqdm.write(f"{task.host}: facts gathered")

       # more actions go here
       other_bar.update()
       tqdm.write(f"{task.host}: done!")


   # we create the first bar named napalm_get_bar
   with tqdm(
       total=len(nr.inventory.hosts), desc="gathering facts",
   ) as napalm_get_bar:
       # we create the second bar named other_bar
       with tqdm(
           total=len(nr.inventory.hosts), desc="other action   ",
       ) as other_bar:
           # we call our grouped task passing both bars
           nr.run(
               task=multiple_progress_bar,
               napalm_get_bar=napalm_get_bar,
               other_bar=other_bar,
           )

It looks a bit daunting due to the nesting but basically we are creating two progress bars, one inside the other and then we just pass them to our grouped task. Finally, the grouped task can update the progress by calling ``bar_name.update()``. You can also add further information using ``tqdm.write("more info!")`` if you want.
