Perun
-----

`Perun <https://perun-aai.org/>`_ is the main "database" of the service where all
important data are stored and retrieved. de.NBI projects are stored as groups with
attributes and individual locations (Bielefeld, Gießen,...) are partly modeled as
Resources. Groups and Attributes are implemented in the :mod:`os_credits.perun` module,
resources are not since we are only interested in their ID's.

Groups
^^^^^^
Groups inside *Perun* are *Projects* inside *de.NBI*. All related API calls to defined
in :mod:`~os_credits.perun.groupsManager`. On initialization they only contain the
attributes passed to the constructor, namely ``project_name`` and ``location_id``, see
:ref:`Measurements`. Required attributes from *Perun*, belonging to the group, are
requested on :func:`~os_credits.perun.group.Group.connect`, see below.

.. autoclass:: os_credits.perun.group.Group
   :members:
   :undoc-members:
   :noindex:

Attributes
^^^^^^^^^^

Most of the attributes are directly assigned to groups but there also ones which are
assigned to a connection between a group and a resource (a group assigned to a
resource). We call this attributes *resource bound*. One example is
:class:`~os_credits.perun.attributes.DenbiCreditTimestamps`.

All currently used attributes can be found in :mod:`~os_credits.perun.attributes`.
Multiple base classes are used to make it easy to add more attributes if required. In
most cases a suitable base class should already be present and only its *Perun* specific
information have to be adapted.

.. inheritance-diagram:: os_credits.perun.attributes.DenbiCreditTimestamps os_credits.perun.attributes.DenbiCreditsGranted
   :parts: 1

.. autoclass:: os_credits.perun.base_attributes.PerunAttribute
   :members:
   :undoc-members:
   :noindex:
