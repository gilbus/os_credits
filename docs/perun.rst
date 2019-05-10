Perun
-----

`Perun <https://perun-aai.org/>`_ is the main "database" of the service where all
important data are stored and retrieved. de.NBI projects are stored as groups with
attributes and individual locations (Bielefeld, Gießen,...) are partly modeled as
Resources. Groups and Attributes are implemented in the :mod:`os_credits.perun` module,
resources are not since we are only interested in their ID's.

Groups
^^^^^^

Most of the attributes are directly assigned to groups but there also ones which are
assigned to a connection between a group and a resource (a group assigned to a
resource). We call this attributes *resource bound*. One example is
:class:`~os_credits.perun.attributes.DenbiCreditTimestamps`.

.. autoclass:: os_credits.perun.group.Group
   :members:
   :undoc-members:
   :noindex:

Attributes
^^^^^^^^^^

.. autoclass:: os_credits.perun.base_attributes.PerunAttribute
   :members:
   :undoc-members:
   :noindex:


.. inheritance-diagram:: os_credits.perun.attributes.DenbiCreditTimestamps os_credits.perun.attributes.DenbiCreditsGranted
   :private-bases:
   :parts: 1
