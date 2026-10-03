Given below is the threading design and implementation for MDA.
- **Interleaved barrel processor** - Switching between the IF, ID, and EX stages in a round the robin fashion. When one thread is fetching, another thread is decoding and the other one is executing.
- **3 independent threads** - 