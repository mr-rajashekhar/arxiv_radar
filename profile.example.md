# Research Profile

Target venues: **OSDI, SOSP, NSDI, SIGCOMM, ASPLOS, EuroSys, ATC, MLSys, SoCC, HotNets**.
Research identity: **LLM-systems researcher.** Currently active at the application / serving layer (XWind / Heron / AI Greenferencing — wind-powered cross-site LLM inference routing and site-local control), with a growing interest in lower layers of the stack: runtime / scheduler, GPU memory & KV-cache, collective communication & RDMA fabrics, OS and kernel-level support for AI, and hardware-software co-design for LLM inference and training.

## INTERESTED_IN

### core: LLM inference serving systems (the dominant topic at OSDI/SOSP/ASPLOS/EuroSys)
- KV-cache management: paging, eviction, quantization, tiered (GPU/CPU/CXL/SSD), multi-level caches
- KV-cache reuse / sharing: prefix caching, RAG cache fusion, cross-request and cross-engine sharing
- Prefill/decode disaggregation and goodput-oriented serving
- Chunked prefills, stall-free scheduling, continuous batching, piggybacking
- Dynamic request scheduling, live migration of in-flight requests across GPUs/sites
- Latency SLOs: TTFT (Time-To-First-Token), TBT (Time-Between-Tokens), P50/P95/P99 E2E latency, goodput
- LoRA / multi-adapter serving, adapter orchestration, multiplexing
- Mixture-of-Experts (MoE) serving: expert placement, routing, and memory pressure
- Speculative decoding, draft-target systems, and cascade/hybrid inference
- Long-context and reasoning-model (o1-style) serving: compute scaling, reasoning-time tradeoffs
- RAG-serving systems: retrieval-compute co-design, cache-augmented generation
- LLM-agent / multi-call application serving (semantic variables, DAG-level optimization)
- Serverless and spot/preemptible inference; checkpoint loading and cold start
- Heterogeneous hardware inference (A100, H100, H200, B200, MI300X, TPU, CPU, PIM, FPGA)
- Tensor / pipeline / sequence / context parallelism for inference; auto-parallelization
- Memory management alternatives to PagedAttention (vAttention-style, virtual memory contiguity)

### sustainability × LLM systems
- Carbon- and renewable-aware scheduling, placement, and routing for compute (wind, solar, grid-carbon signals)
- Behind-the-meter / on-site renewable co-location for AI compute (modular DCs, SuperPODs at wind farms)
- Power variability / intermittent compute; right-sizing at low percentiles of renewable generation
- Spatial and temporal complementarity across sites for demand-supply matching
- Power capping, DVFS, frequency downclocking, and node idling/shutdown under power constraints
- Datacenter power modulation control — meeting power targets with minimal SLO impact
- Embodied carbon vs. operational carbon tradeoffs in GPU clusters and interconnects
- Grid-interactive datacenters, demand response, and T&D loss considerations

### LLM training systems (NSDI/SOSP/EuroSys staples)
- Distributed training at mega-scale: 3D parallelism, ZeRO, FSDP, hot-switching parallelism
- Fault tolerance, failure localization, and elasticity in multi-thousand-GPU clusters
- Checkpointing at scale (tiered, async, replay); straggler mitigation
- Collective-communication optimization (AllReduce, All-to-All); overlap with compute
- RLHF/RL training infrastructure; post-training fine-tuning pipelines

### GPU networking & collective comms (SIGCOMM/NSDI/HotNets)
- RDMA/RoCE for AI: white-boxing, congestion control, packet-level control, lossless fabrics
- Software transport layers for GPU networking (UCCL-style); NIC offload; NCCL alternatives
- Collective tuning / autotuning across topologies (fat-tree, rail-optimized, dragonfly)
- In-network aggregation, SHARP-style offload for training
- Topology-aware scheduling; cross-DC and WAN-aware ML communication
- Optical interconnects, reconfigurable fabrics for AI clusters

### Scheduling & resource management (ATC/SoCC/EuroSys)
- Multi-tenant GPU scheduling, fair sharing, preemption under SLOs
- Goodput- and SLO-aware admission control for LLM serving
- Energy-aware job coscheduling; per-watt performance optimization
- Telemetry-driven reactive control loops (queue depth, KV cache, latency, power)
- Workload- and output-length-prediction-free designs (or lightweight predictors)

### Evaluation, datasets, methodology
- Production-scale LLM traces (coding, chat, agentic); mixed workloads with long context
- Benchmarking serving systems end-to-end (goodput, SLO attainment, energy/token)
- Simulators for large GPU clusters (SimAI-style) and power/carbon co-simulators

## NOT_INTERESTED_IN

- Pure ML theory and new transformer/attention architectures without systems or serving angle
- Model algorithm papers (new optimizers, novel losses, representation learning) without system evaluation
- NLP applications / task-specific LLM fine-tuning without a systems contribution
- Space-based computing demonstrations for AI power (outside my scope)
- On-site fossil generation for compute power (gas turbines, fuel cells) unless compared to renewables
- Nuclear deployment policy / timeline studies without systems implications
- Crypto-mining workloads
- Non-AI datacenter HPC papers (e.g., climate simulation, CFD) unless methods transfer to LLM serving
- Surveys, position papers without measurement, and pure benchmarking tools lacking novelty
- Quantization / compression papers that are purely algorithmic with no serving impact study
- Federated learning, privacy-preserving ML, differential privacy (orthogonal to my work)
- Diffusion / vision / multimodal serving only — include *only* if techniques generalize to LLM serving
