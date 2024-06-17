using DelimitedFiles
using Random
using CSV
using Statistics
using Printf
using LinearAlgebra

struct Results
    thresholds::Dict{Float64, Vector{Float64}}
    ground_truth::Vector{Float64}
    min_buff_dim::Int
    ticks_per_sec::Int
    x_limit::Int
    limit::Float64
    bases::Vector{String}

    function Results()
        self = new(Dict{Float64, Vector{Float64}}(), [0.52,0.56,0.60,0.64,0.68,0.72,0.76,0.8,0.84,0.88,0.92,0.96,1.0], 5, 10, 100, 0.8, String[])
        base = abspath("")
        for elem in sort(readdir(base))
            if '.' ∉ elem
                selem = split(elem, '_')
                if selem[1] == "Oresults" || selem[1] == "Presults"
                    push!(self.bases, joinpath(base, elem))
                end
            end
        end
        for gt in self.ground_truth
            _thresholds = collect(50:100)
            f_thresholds = map(x -> round(x * 0.01, digits=2), _thresholds)
            self.thresholds[gt] = f_thresholds
        end
        return self
    end

    function extract_k_data(self, base, path_temp, max_steps, communication, n_agents, msg_exp_time, sub_path, data_type="all")
        max_buff_size = n_agents - 1
        act_results = Dict()
        num_runs = Int(floor(length(readdir(sub_path)) / n_agents))
        msgs_bigM_1 = [Array{Int64, 1}[] for _ in 1:n_agents]
        act_bigM_1 = [Array{Int64, 1}[] for _ in 1:n_agents]
        act_bigM_2 = [Array{Int64, 1}[] for _ in 1:n_agents]
        msgs_M_1 = [Array{Int64, 1}[] for _ in 1:num_runs]
        act_M_1 = [Array{Int64, 1}[] for _ in 1:num_runs]
        act_M_2 = [Array{Int64, 1}[] for _ in 1:num_runs]

        states_by_gt = [Array{Int64, 2}[] for _ in 1:length(self.ground_truth)]
        for gt in 1:length(self.ground_truth)
            runs_states = [Array{Int64, 2}[] for _ in 1:num_runs]
            num_committed = ceil(Int, n_agents * self.ground_truth[gt])
            for i in 1:num_runs
                ones = 0
                agents_state = zeros(Int, n_agents)
                while true
                    for j in 1:n_agents
                        if agents_state[j] == 0
                            tmp = rand(Bool) ? 1 : 0
                            if tmp == 1 && ones < num_committed
                                ones += 1
                                agents_state[j] = tmp
                            end
                        end
                        if ones >= num_committed
                            break
                        end
                    end
                    if ones >= num_committed
                        break
                    end
                end
                runs_states[i] = agents_state
            end
            states_by_gt[gt] = vcat(states_by_gt[gt], hcat(runs_states...))
        end

        a_ = 0
        prev_id = -1
        for elem in sort(readdir(sub_path))
            if '.' in elem
                selem = split(elem, '.')
                if selem[end] == "tsv" && startswith(selem[1], "quorum")
                    a_ += 1
                    seed = parse(Int, split(selem[1], '#')[end])
                    agent_id = parse(Int, split(split(selem[1], '__')[1], '#')[1])
                    if prev_id != agent_id
                        a_ = 0
                    end
                    if a_ == 0
                        prev_id = agent_id
                    end
                    f = open(joinpath(sub_path, elem))
                    reader = CSV.Reader(f)
                    log_count = 0
                    for row in reader
                        log_count += 1
                        if log_count % self.ticks_per_sec == 0
                            log_count = 0
                            msgs = []
                            broadcast_c = 0
                            re_broadcast_c = 0
                            for val in row
                                if count(x -> x == '\t', val) == 0
                                    if val != '-'
                                        push!(msgs, parse(Int, val))
                                    else
                                        push!(msgs, 0)
                                    end
                                else
                                    val = split(val, '\t')
                                    if val[1] != ""
                                        push!(msgs, parse(Int, val[1]))
                                    end
                                    broadcast_c = val[2]
                                    re_broadcast_c = val[3]
                                end
                            end
                            if data_type in ["all", "freq"]
                                append!(act_M_1[seed], broadcast_c)
                                append!(act_M_2[seed], re_broadcast_c)
                            end
                            while length(msgs) < max_buff_size
                                push!(msgs, -1)
                            end
                            if isempty(msgs_M_1[seed])
                                msgs_M_1[seed] = [msgs]
                            else
                                push!(msgs_M_1[seed], msgs)
                            end
                        end
                    end
                    close(f)
                    if length(msgs_M_1[seed]) != max_steps
                        println("$sub_path\nrun: $seed agent: $(length(msgs_M_1[seed])) tot lines: $(length(msgs_M_1[seed]))")
                    end
                    if seed == num_runs
                        msgs_bigM_1[agent_id] = msgs_M_1
                        msgs_M_1 = [Array{Int64, 1}[] for _ in 1:num_runs]
                        if data_type in ["all", "freq"]
                            act_bigM_1[agent_id] = act_M_1
                            act_bigM_2[agent_id] = act_M_2
                            act_M_1 = [Array{Int64, 1}[] for _ in 1:num_runs]
                            act_M_2 = [Array{Int64, 1}[] for _ in 1:num_runs]
                        end
                    end
                end
            end
        end

        if data_type in ["all", "quorum"]
            info_vec = split(sub_path, '/')
            t_messages = split(sub_path, '#')[end]
            algo = info_vec[5][1]
            arenaS = info_vec[5][end-3:end]
            BUFFERS = []
            if arenaS == "small"
                BUFFERS = [20, 22, 23, 23.01, 24]
            elseif arenaS == "big"
                if n_agents == 25
                    BUFFERS = [11, 15, 17, 19, 21]
                elseif n_agents == 100
                    BUFFERS = [41, 56, 65, 74, 83]
                end
            end
            if algo == 'P'
                for buf in 1:length(BUFFERS)
                    messages = compute_meaningful_msgs(self, msgs_bigM_1, BUFFERS[buf], algo, buf + 1, length(BUFFERS))
                    write_msgs_data(self, "messages_resume.csv", [arenaS, algo, communication, n_agents, BUFFERS[buf], messages])
                    for gt in 1:length(self.ground_truth)
                        results = compute_quorum_vars_on_ground_truth(self, algo, msgs_bigM_1, states_by_gt[gt], BUFFERS[buf], gt + 1, length(self.ground_truth))
                        for thr in self.thresholds[self.ground_truth[gt]]
                            quorum_results = Dict()
                            states = compute_quorum(self, results[1], results[2], self.min_buff_dim, thr)
                            quorum_results[(self.ground_truth[gt], self.min_buff_dim, thr)] = (states, results[1])
                            dump_times(self, algo, 0, quorum_results, base, path_temp, self.ground_truth[gt], self.min_buff_dim, BUFFERS[buf], self.limit)
                            dump_quorum_and_buffer(self, algo, 0, quorum_results, base, path_temp, self.ground_truth[gt], self.min_buff_dim, BUFFERS[buf])
                            gc()
                            recovery_res = compute_recovery(self, self.ground_truth[gt], thr, states)
                            dump_recovery(self, algo, 0, recovery_res, base, path_temp, self.ground_truth[gt], self.min_buff_dim, BUFFERS[buf])
                            gc()
                        end
                        gc()
                    end
                end
            else
                messages = compute_meaningful_msgs(self, msgs_bigM_1, t_messages, algo, 1, 1)
                write_msgs_data(self, "messages_resume.csv", [arenaS, algo, communication, n_agents, t_messages, messages])
                for gt in 1:length(self.ground_truth)
                    results = compute_quorum_vars_on_ground_truth(self, algo, msgs_bigM_1, states_by_gt[gt], 0, gt + 1, length(self.ground_truth))
                    for thr in self.thresholds[self.ground_truth[gt]]
                        quorum_results = Dict()
                        states = compute_quorum(self, results[1], results[2], self.min_buff_dim, thr)
                        quorum_results[(self.ground_truth[gt], self.min_buff_dim, thr)] = (states, results[1])
                        dump_times(self, algo, 0, quorum_results, base, path_temp, self.ground_truth[gt], self.min_buff_dim, msg_exp_time, self.limit)
                        dump_quorum_and_buffer(self, algo, 0, quorum_results, base, path_temp, self.ground_truth[gt], self.min_buff_dim, msg_exp_time)
                        gc()
                        recovery_res = compute_recovery(self, self.ground_truth[gt], thr, states)
                        dump_recovery(self, algo, 0, recovery_res, base, path_temp, self.ground_truth[gt], self.min_buff_dim, msg_exp_time)
                        gc()
                    end
                    gc()
                end
            end
        end

        if data_type in ["all", "freq"]
            act_results[0] = (act_bigM_1, act_bigM_2)
            dump_msg_freq(self, algo, 2, act_results, length(act_M_1), base, path_temp, msg_exp_time)
            gc()
        end

        gc()
    end

    function compute_quorum_vars_on_ground_truth(self::Results, algo::String, m1, states, buf_lim::Int, gt::Float64, gt_dim::Int)
        println("--- Processing data $gt/$gt_dim ---")
        tmp_dim_0 = [Vector{Float64}[] for _ in 1:length(m1[1])]
        tmp_ones_0 = [Vector{Float64}[] for _ in 1:length(m1[1])]

        for i in 1:length(states)
            tmp_dim_1 = [Vector{Float64}[] for _ in 1:length(m1)]
            tmp_ones_1 = [Vector{Float64}[] for _ in 1:length(m1)]
            for j in 1:length(states[i])
                tmp_dim_2 = Float64[]
                tmp_ones_2 = Float64[]
                for t in 1:length(m1[j][i])
                    dim = 1.0
                    ones = states[i][j]
                    tmp = filter(x -> x != -1, m1[j][i][t])
                    start = 1
                    if algo == 'P' && length(tmp) > buf_lim
                        start = length(tmp) - buf_lim + 1
                    end
                    for z in start:length(tmp)
                        dim += 1
                        ones += states[i][m1[j][i][t][z]]
                    end
                    push!(tmp_dim_2, dim)
                    push!(tmp_ones_2, ones)
                end
                tmp_dim_1[j] = tmp_dim_2
                tmp_ones_1[j] = tmp_ones_2
            end
            tmp_dim_0[i] = tmp_dim_1
            tmp_ones_0[i] = tmp_ones_1
        end
        return (tmp_dim_0, tmp_ones_0)
    end

    function compute_quorum(m1, m2, minus::Float64, threshold::Float64)
        out = copy(m1)
        for i in 1:length(m1)
            for j in 1:length(m1[i])
                for k in 1:length(m1[i][j])
                    out[i][j][k] = if m1[i][j][k] - 1 >= minus && m2[i][j][k] >= threshold * m1[i][j][k]
                                    1
                                else
                                    0
                                end
                end
            end
        end
        return out
    end

    function compute_meaningful_msgs(self::Results, data, limit::Int, algo::String, buf::Int, buf_dim::Int)
        println("--- Computing avg buffer dimension $buf/$buf_dim ---")
        data_partial = Float64[]
        for ag in 1:length(data)
            runs = Float64[]
            for rn in 1:length(data[ag])
                tmp = zeros(Int, length(data[1][1]))
                for tk in 1:length(data[ag][rn])
                    flag = Int[]
                    for el in 1:length(data[ag][rn][tk])
                        if algo == 'P' && el >= limit
                            break
                        elseif data[ag][rn][tk][el] ∉ flag && data[ag][rn][tk][el] != -1
                            push!(flag, data[ag][rn][tk][el])
                            tmp[tk] += 1
                        end
                    end
                end
                if length(runs) == 0
                    runs = [tmp]
                else
                    runs = vcat(runs, [tmp])
                end
            end
            if length(data_partial) == 0
                data_partial = [runs]
            else
                data_partial = vcat(data_partial, [runs])
            end
        end
        msgs_summation = zeros(length(data_partial[1][1]))
        for ag in 1:length(data_partial)
            for rn in 1:length(data_partial[ag])
                for tk in 1:length(data_partial[ag][rn])
                    msgs_summation[tk] += data_partial[ag][rn][tk]
                end
            end
        end
        for tk in 1:length(msgs_summation)
            msgs_summation[tk] /= length(data_partial)
            msgs_summation[tk] = round(msgs_summation[tk] / length(data_partial[1]), digits=3)
        end
        return msgs_summation
    end

    function write_msgs_data(file_name::String, data::Vector{Any})
        header = ["ArenaSize", "algo", "broadcast", "n_agents", "buff_dim", "data"]
        write_header = !isfile(joinpath(abspath(""), "msgs_data", file_name))

        if !isdir(joinpath(abspath(""), "msgs_data"))
            mkdir(joinpath(abspath(""), "msgs_data"))
        end

        open(joinpath(abspath(""), "msgs_data", file_name), "a") do fw
            if write_header
                writedlm(fw, [header], '\t')
            end
            writedlm(fw, [data], '\t')
        end
    end

    function dump_resume_csv(self, algo, indx, bias, value, data_in, data_std, base, path, COMMIT, THRESHOLD, MINS, MSG_EXP_TIME, n_runs)
        static_fields = ["CommittedPerc", "Threshold", "MinBuffDim", "MsgExpTime"]
        static_values = [COMMIT, THRESHOLD, MINS, MSG_EXP_TIME]
    
        if !isdir("proc_data")
            mkdir("proc_data")
        end
    
        write_header = false
        name_fields = []
        values = []
    
        file_name = algo == 'O' ? "Oaverage_resume_r#$n_runs##_a#$(split(base, '_')[end]).csv" : "Paverage_resume_r#$n_runs##_a#$(split(base, '_')[end]).csv"
        
        if !isfile(joinpath("proc_data", file_name))
            write_header = true
        end
    
        tmp_b = split(base, '/')
        tmp_p = split(path, '/')
        for i in tmp_p
            if i ∉ tmp_b
                tmp = split(i, "#")
                push!(name_fields, tmp[1])
                push!(values, tmp[2])
            end
        end
    
        append!(name_fields, static_fields)
        append!(values, static_values)
    
        push!(name_fields, "type")
        push!(name_fields, "mean_value")
        push!(name_fields, "data")
        push!(name_fields, "std")
    
        value_type = if indx + bias == -1
            "times"
        elseif indx + bias == 0
            "swarm_state"
        elseif indx + bias == 1
            "quorum_length"
        elseif indx + bias == 2
            "broadcast_msg"
        elseif indx + bias == 3
            "rebroadcast_msg"
        end
        push!(values, value_type)
        push!(values, value)
        push!(values, data_in)
        push!(values, data_std)
    
        df = DataFrame(; name_fields .=> values)
        CSV.write(joinpath("proc_data", file_name), df, append = !write_header)
    end
    
    function dump_msg_freq(self, algo, bias, data_in, dMR, BASE, PATH, MSG_EXP_TIME)
        for l in 1:length(data_in[0])
            multi_run_data = data_in[0][l]
            if multi_run_data !== nothing
                flag2 = fill(-1.0, length(multi_run_data[1][1]))
                for i in 1:length(multi_run_data[1])
                    flag1 = fill(-1.0, length(multi_run_data[1][1]))
                    for j in 1:length(multi_run_data)
                        for z in 1:length(multi_run_data[j][i])
                            flag1[z] = flag1[z] == -1 ? multi_run_data[j][i][z] : flag1[z] + multi_run_data[j][i][z]
                        end
                    end
                    for j in 1:length(flag1)
                        flag1[j] /= length(multi_run_data)
                        flag2[j] = flag2[j] == -1 ? flag1[j] : flag2[j] + flag1[j]
                    end
                end
                for i in 1:length(flag2)
                    flag2[i] /= length(multi_run_data[1])
                end
    
                fstd2 = fill([-1.0 for _ in 1:length(multi_run_data[1][1])], length(multi_run_data[1]))
                fstd3 = fill(-1.0, length(multi_run_data[1][1]))
                for i in 1:length(multi_run_data[1])
                    fstd1 = fill(-1.0, length(multi_run_data[1][1]))
                    for z in 1:length(multi_run_data[1][1])
                        std_tmp = [multi_run_data[j][i][z] for j in 1:length(multi_run_data)]
                        fstd1[z] = std(std_tmp)
                    end
                    fstd2[i] = fstd1
                end
                for z in 1:length(fstd3)
                    median_array = [fstd2[i][z] for i in 1:length(fstd2)]
                    fstd3[z] = self.extract_median(median_array)
                end
                self.dump_resume_csv(algo, l, bias, '-', round.(flag2, digits=2), round.(fstd3, digits=3), BASE, PATH, "-", "-", "-", MSG_EXP_TIME, dMR)
            end
        end
    end
    
    function dump_quorum_and_buffer(self, algo, bias, data_in, BASE, PATH, COMMIT, MINS, MSG_EXP_TIME)
        for t in 1:length(self.thresholds[COMMIT])
            threshold = self.thresholds[COMMIT][t]
            if data_in[(COMMIT, MINS, threshold)] !== nothing
                for l in 1:length(data_in[(COMMIT, MINS, threshold)])
                    if data_in[(COMMIT, MINS, threshold)][l] !== nothing
                        mean_val = 0.0
                        multi_run_data = data_in[(COMMIT, MINS, threshold)][l]
                        flag2 = fill(-1.0, length(multi_run_data[1][1]))
                        for i in 1:length(multi_run_data)
                            flag1 = fill(-1.0, length(multi_run_data[i][1]))
                            flagmv = fill(-1.0, length(multi_run_data[i]))
                            for j in 1:length(multi_run_data[i])
                                for z in 1:length(multi_run_data[i][j])
                                    flag1[z] = flag1[z] == -1 ? multi_run_data[i][j][z] : flag1[z] + multi_run_data[i][j][z]
                                    flagmv[j] = flagmv[j] == -1 ? multi_run_data[i][j][z] : flagmv[j] + multi_run_data[i][j][z]
                                end
                                flagmv[j] /= length(multi_run_data[i][j])
                            end
                            mean_val += sum(flagmv)
                            for j in 1:length(flag1)
                                flag1[j] /= length(multi_run_data[i])
                                flag2[j] = flag2[j] == -1 ? flag1[j] : flag2[j] + flag1[j]
                            end
                        end
                        for i in 1:length(flag2)
                            flag2[i] /= length(multi_run_data)
                        end
                        mean_val /= length(multi_run_data)
                        
                        fstd2 = fill([-1.0 for _ in 1:length(multi_run_data[1][1])], length(multi_run_data))
                        fstd3 = fill(-1.0, length(multi_run_data[1][1]))
                        for i in 1:length(multi_run_data)
                            fstd1 = fill(-1.0, length(multi_run_data[i][1]))
                            for z in 1:length(multi_run_data[i][1])
                                std_tmp = [multi_run_data[i][j][z] for j in 1:length(multi_run_data[i])]
                                fstd1[z] = std(std_tmp)
                            end
                            fstd2[i] = fstd1
                        end
                        for z in 1:length(fstd3)
                            median_array = [fstd2[i][z] for i in 1:length(fstd2)]
                            fstd3[z] = self.extract_median(median_array)
                        end
                        if l == 0
                            self.dump_resume_csv(algo, l, bias, round(mean_val, digits=2), round.(flag2, digits=2), round.(fstd3, digits=3), BASE, PATH, COMMIT, threshold, MINS, MSG_EXP_TIME, length(multi_run_data))
                        else
                            self.dump_resume_csv(algo, l, bias, '-', round.(flag2, digits=2), round.(fstd3, digits=3), BASE, PATH, COMMIT, threshold, MINS, MSG_EXP_TIME, length(multi_run_data))
                        end
                    end
                end
            end
        end
    end
    
    function dump_times(self, algo, bias, data_in, BASE, PATH, COMMIT, MINS, MSG_EXP_TIME, limit)
        for t in 1:length(self.thresholds[COMMIT])
            threshold = self.thresholds[COMMIT][t]
            if data_in[(COMMIT, MINS, threshold)] !== nothing
                multi_run_data = data_in[(COMMIT, MINS, threshold)][1]
                times = fill(length(multi_run_data[1][1]), length(multi_run_data))
                for i in 1:length(multi_run_data)
                    for z in 1:length(multi_run_data[i][1])
                        sum_val = sum(multi_run_data[i][j][z] for j in 1:length(multi_run_data[i]))
                        if sum_val >= limit * length(multi_run_data[i])
                            times[i] = z
                            break
                        end
                    end
                end
                times = sort(times)
                self.dump_resume_csv(algo, -1, bias, '-', times, '-', BASE, PATH, COMMIT, threshold, MINS, MSG_EXP_TIME, length(multi_run_data))
            end
        end
    end
    
    function extract_median(self, array)
        sortd_arr = sort(array)
        len_arr = length(sortd_arr)
        if iseven(len_arr)
            return (sortd_arr[Int(len_arr // 2)] + sortd_arr[Int(len_arr // 2) + 1]) * 0.5
        else
            return sortd_arr[Int(ceil(len_arr / 2))]
        end
    end
    
end

