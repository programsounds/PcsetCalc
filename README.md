# PcsetCalc

An application for pitch-class set and modal set complex queries and operations.

## Notes on symmetrical sets 

- The text box showing the degree of symmetry indicates whether the current set is inversionally symmetrical and has any axis of symmetry.
- To look up the axis of symmetry (i.e., sum), check the index vector: for the axis of sum n, n is the index number which corresponds with the cardinal number of the set.  
- A handful of the MSC members are inversionally symmetrical. Note that none of the modal nexus sets are inversionally symmetrical (degree of inversional symmetry is 0).
- For the profile of the current set, Tn/TnI transformation level of the set is shown with a single symbol for the simplicity, that is, if it is a symmetrical set, the Tn level with the smallest transposition number represents the transformation level.

## Dependencies

| Package                                           | Version | Description                                                            |
|---------------------------------------------------|---------|------------------------------------------------------------------------|
| [pcpy](https://pypi.org/project/pcpy/)            | 0.1.0   | A Python package for pcset operations, relation measures, and queries. |
| [OSCpy](https://pypi.org/project/oscpy/)          | 0.6.0   | A modern implementation of OSC for python2/3                           |
| [rtmini](https://pypi.org/project/python-rtmidi/) | 1.5.6   | A Python binding for the RtMidi C++ library                            |
| [PyQt6](https://pypi.org/project/PyQt6/)          | 6.5.2   | Python bindings for the Qt cross-platform application toolkit          |



## To Do

- Documentation


