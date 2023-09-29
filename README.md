# PcsetCalc

App for pcset and MSC queries and operations.

### Notes on symmetrical sets 

- The text box showing the degree of symmetry indicates whether the current set is inversionally symmetrical and has any axis of symmetry.
- To look up the axis of symmetry (i.e., sum), check the index vector: for the axis of sum n, n is the index number which corresponds with the cardinal number of the set.  
- A handful of the MSC members are inversionally symmetrical. Note that none of the modal nexus sets are inversionally symmetrical (degree of inversional symmetry is 0).
- For the profile of the current set, Tn/TnI transformation level of the set is shown with a single symbol for the simplicity, that is, if it is a symmetrical set, the Tn level with the smallest transposition number represents the transformation level.

### Known issue

- As pyOSC causes an error on the closing socket, the current UDP port cannot be changed while the program is running. For now, after changing the port in the connection window, just restart the program to make the change in effect.
- Menubar items cannot be clicked after the app starts up until its focus is set to others and back to it.
