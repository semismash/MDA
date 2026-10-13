- MDA classifies CPU operational changes into two main categories -
	- **Events** - Changes in hardware state which can be handled by software deterministically.
	- **Interrupts** - Sudden changes in a CPU's control flow which have to be handled at a hardware level.

### Events
Events are changes in the hardware state that can be observed in the CPU. They do not represent changes in the control flow itself, and they can be handled via software, hence preserving determinism.
- Events are latched. When an event occurs, it gets latched to high to be handled later by the suitable even handler. Events are not required to be explicitly handled.
- Examples of events include, but are not limited to - Pin rising and falling edges, memory subsystem events, channel state changes, expired timers, software triggered events (tentative) etc.
- Events can be observed using a combination of CPU flags (via conditional jumps) and dedicated instructions, allowing the program to handle an event when it occurs.