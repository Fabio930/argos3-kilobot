using Logging
using ArgParse
using Distributed
using Dates
using FilePathsBase
using Printf
using CSV
using DataFrames
using data_extractorJ as dex

# Initialize distributed processes
addprocs()

# Setup logging
function setup_logging()
    global_logger(ConsoleLogger(stdout, Logging.Debug))
end

# Check command line inputs
function check_inputs()
    ticks = 10
    data_type = "all"
    
    parser = ArgParseSettings()
    @add_arg_table! parser begin
        "-d"
        "--data_type"
        help = "Data type (all, quorum, freq)"
        arg_type = String
        default = "all"
        
        "-t"
        "--ticks"
        help = "Ticks per second"
        arg_type = Int
        default = 10
    end
    
    args = parse_args(parser)
    
    data_type = get(args, "data_type", "all")
    ticks = get(args, "ticks", 10)
    
    if data_type ∉ ["all", "quorum", "freq"]
        error("BAD format -d input type\nallowed entries are: all, quorum or freq --EXIT--")
    end
    
    if ticks <= 0
        error("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
    end
    
    return ticks, data_type
end

# Process folder with retries and memory management
@everywhere function process_folder(task)
    base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time, sub_path, ticks_per_sec = task
    retry_count = 50

    while retry_count > 0
        try
            # Memory usage logging
            mem_usage_before = Sys.total_memory() - Sys.free_memory()
            @info "Memory usage before processing $sub_path: $(mem_usage_before / (1024 * 1024)) MB"

            results = dex.Results()
            results.ticks_per_sec = ticks_per_sec
            results.extract_k_data(base, dtemp, exp_length, communication, n_agents, msg_exp_time, sub_path, data_type)
            GC.gc()

            # Memory usage logging
            mem_usage_after = Sys.total_memory() - Sys.free_memory()
            @info "Memory usage after processing $sub_path: $(mem_usage_after / (1024 * 1024)) MB"

            break
        catch e
            if e isa OutOfMemoryError
                @error "MemoryError processing $sub_path: $e"
                retry_count -= 1
                if retry_count > 0
                    @info "Retrying $sub_path ($retry_count) after MemoryError"
                    sleep(600)  # Delay before retrying
                else
                    @error "Failed $sub_path due to MemoryError"
                end
                GC.gc()
            else
                @error "Error processing $sub_path: $e"
                GC.gc()
                break
            end
        end
    end
end

# Main function
function main()
    setup_logging()
    ticks_per_sec, data_type = check_inputs()

    tasks = []

    for base in dex.Results().bases
        for adir in sort(readdir(base))
            if '.' ∉ adir && '#' ∈ adir
                pre_apath = joinpath(base, adir)
                exp_length = parse(Int, split(adir, '#')[2])
                for dir in sort(readdir(pre_apath))
                    if '.' ∉ dir && '#' ∈ dir
                        communication = parse(Int, split(dir, '#')[2])
                        pre_path = joinpath(pre_apath, dir)
                        for zdir in sort(readdir(pre_path))
                            if '.' ∉ zdir && '#' ∈ zdir
                                n_agents = parse(Int, split(zdir, '#')[2])
                                dtemp = joinpath(pre_path, zdir)
                                for pre_folder in sort(readdir(dtemp))
                                    if '.' ∉ pre_folder
                                        msg_exp_time = parse(Int, split(pre_folder, '#')[-1])
                                        sub_path = joinpath(dtemp, pre_folder)
                                        push!(tasks, (base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time, sub_path, ticks_per_sec))
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end

    # Using a manager to handle the queue
    task_queue = Distributed.SharedArray{Tuple}(length(tasks))

    for (i, task) in enumerate(tasks)
        task_queue[i] = task
    end

    active_processes = []
    total_memory = Sys.total_memory() / (1024 * 1024)  # Total memory in MB
    memory_per_process_25 = 1006632.96 / 1024  # Memory used by each process with 25 agents
    memory_per_process_100 = 8053063.68 / 1024  # Memory used by each process with 100 agents

    while !isempty(task_queue) || !isempty(active_processes)
        # Calculate total memory used by active processes
        total_memory_used = sum(memory_per_process_25 if n_agents == 25 else memory_per_process_100 for p, n_agents in active_processes)

        # Launch new processes if there is room
        while total_memory_used + min(memory_per_process_25, memory_per_process_100) <= total_memory && !isempty(task_queue)
            task = popfirst!(task_queue)
            n_agents = task[4]
            required_memory = memory_per_process_25 if n_agents == 25 else memory_per_process_100
            if total_memory_used + required_memory <= total_memory
                p = @spawn process_folder(task)
                push!(active_processes, (p, n_agents))
                total_memory_used += required_memory
            else
                # Requeue the task if there's not enough memory
                unshift!(task_queue, task)
                break
            end
        end

        # Check for completed processes
        for (p, n_agents) in active_processes
            if !isready(p)
                wait(p)
                deleteat!(active_processes, findfirst(x -> x[1] == p, active_processes))
                if n_agents == 25
                    total_memory_used -= memory_per_process_25
                elseif n_agents == 100
                    total_memory_used -= memory_per_process_100
                end
            end
        end

        sleep(300)  # Avoid busy-waiting
    end

    @info "All tasks completed."
end

# Run the main function
main()
