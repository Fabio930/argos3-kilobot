/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#include "BestN_ALF.h"
#include <algorithm>
#include <cctype>
#include <cmath>

namespace {
UInt32 NextXorShift32(UInt32& unState) {
    unState ^= (unState << 13);
    unState ^= (unState >> 17);
    unState ^= (unState << 5);
    return unState;
}

UInt8 ControlModeFromString(const std::string& strControl) {
    if(strControl == "static") return 0;
    if(strControl == "linear") return 1;
    if(strControl == "sigmoid") return 2;
    if(strControl == "polynomial") return 3;
    return 0;
}

std::string NormalizeDistributionString(const std::string& strValue) {
    std::string strOut = strValue;
    strOut.erase(0, strOut.find_first_not_of(" \t\r\n"));
    strOut.erase(strOut.find_last_not_of(" \t\r\n") + 1);
    std::transform(strOut.begin(), strOut.end(), strOut.begin(),
                   [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
    if(strOut.empty()) {
        return "random";
    }
    return strOut;
}

std::string g_strOptionsDistribution = "random";
}

/****************************************/
/****************************************/

CBestN_ALF::CBestN_ALF() :
    m_unDataAcquisitionFrequency(10),
    m_unIdAware(1),
    m_unPrioritySamplingK(0),
    m_bInitialFloorSetupAllowed(true),
    m_bVariationFloorSetupAllowed(false){
        c_rng = CRandom::CreateRNG("argos");
}

/****************************************/
/****************************************/

CBestN_ALF::~CBestN_ALF(){}

/****************************************/
/****************************************/

void CBestN_ALF::Init(TConfigurationNode& t_node){
    /* Initialize ALF*/
    CALF::Init(t_node);
}

/****************************************/
/****************************************/

void CBestN_ALF::Reset(){
}

/****************************************/
/****************************************/

void CBestN_ALF::Destroy(){
}

/****************************************/
/****************************************/

void CBestN_ALF::PostStep(){
    if(variation_time > 0){
        m_fTimeInSeconds = GetSpace().GetSimulationClock()/CPhysicsEngine::GetInverseSimulationClockTick();
        if(m_fTimeInSeconds >= (variation_time - 1.0) && m_fTimeInSeconds < variation_time) {
            m_bVariationFloorSetupAllowed = true;
        }

        if(m_fTimeInSeconds >= variation_time){
            const UInt8 unEtaQNow = static_cast<UInt8>(std::round(eta_stop * 127.0));
            if(unEtaQNow != m_unEtaQ){
                m_unEtaQ = unEtaQNow;
                SetupFloorColorMap();
            }
            variation_time = 0;
        }
    }
}

/****************************************/
/****************************************/
void CBestN_ALF::SetupInitialKilobotStates(){
    m_vecKilobotState.resize(m_tKilobotEntities.size());
    m_vecLastTimeMessaged.resize(m_tKilobotEntities.size());
    m_vecStart_experiment.resize(m_tKilobotEntities.size());
    m_vecKilobotPositions.resize(m_tKilobotEntities.size());
    m_vecKilobotOrientations.resize(m_tKilobotEntities.size());
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, m_tKilobotEntities.size() * m_fTimeForAMessage / 3.0);
    UInt32 unTotalRobots = m_tKilobotEntities.size();
    UInt32 unSpecialRobots = static_cast<UInt32>(unTotalRobots * init_distr);
    UInt8 unSpecialOption = 0; 
    if(bTargetRandomWorse && options > 1) {
        unSpecialOption = c_rng->Uniform(CRange<UInt32>(1, options)); 
    } else {
        unSpecialOption = 0;
    }
    std::vector<UInt8> vecOtherOptions;
    for(UInt8 i = 0; i < options; ++i) {
        if(i != unSpecialOption) {
            vecOtherOptions.push_back(i);
        }
    }
    for(UInt16 it = 0; it < unTotalRobots; it++) {
        UInt16 unKilobotID = GetKilobotId(*m_tKilobotEntities[it]);
        
        if(it < unSpecialRobots) {
            m_vecKilobotState[unKilobotID] = unSpecialOption;
        } 
        else {
            if (!vecOtherOptions.empty()) {
                UInt32 idx = (it - unSpecialRobots) % vecOtherOptions.size();
                m_vecKilobotState[unKilobotID] = vecOtherOptions[idx];
            } else {
                m_vecKilobotState[unKilobotID] = unSpecialOption;
            }
        }
        SetupInitialKilobotState(*m_tKilobotEntities[it]);
    }
}
/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupVirtualEnvironments(TConfigurationNode& t_tree){
    CSimulator &simulator = GetSimulator();
    m_random_seed = simulator.GetRandomSeed();
    /* Get the structure variables from the .argos file*/
    TConfigurationNode& tHierarchicalStructNode=GetNode(t_tree,"bestN");
    /* Get dimensions and quality scaling factor*/
    GetNodeAttribute(tHierarchicalStructNode,"rebroadcast",rebroadcast);
    GetNodeAttribute(tHierarchicalStructNode,"options",options);
    GetNodeAttribute(tHierarchicalStructNode,"variation_time",variation_time);
    GetNodeAttribute(tHierarchicalStructNode,"eta_init",eta_init);
    GetNodeAttribute(tHierarchicalStructNode,"eta_stop",eta_stop);
    std::string strInitDistr;
    GetNodeAttribute(tHierarchicalStructNode, "init_distr", strInitDistr);
    strInitDistr.erase(0, strInitDistr.find_first_not_of(" \t\r\n"));
    strInitDistr.erase(strInitDistr.find_last_not_of(" \t\r\n") + 1);
    bTargetRandomWorse = false;
    if(!strInitDistr.empty() && strInitDistr.back() == 'r') {
        bTargetRandomWorse = true;
        strInitDistr.pop_back();
    }
    init_distr = std::stof(strInitDistr);
    GetNodeAttribute(tHierarchicalStructNode,"msgs_timeout",msgs_timeout);
    GetNodeAttribute(tHierarchicalStructNode,"msgs_n_hops",msgs_n_hops);
    GetNodeAttributeOrDefault(tHierarchicalStructNode,"adaptive_comm",adaptive_comm,static_cast<UInt8>(0));
    GetNodeAttributeOrDefault(tHierarchicalStructNode,"id_aware",m_unIdAware,static_cast<UInt8>(1));
    GetNodeAttributeOrDefault(tHierarchicalStructNode,"hop_count",m_unhop_count,static_cast<UInt8>(0));
    GetNodeAttributeOrDefault(tHierarchicalStructNode,"priority_sampling_k",m_unPrioritySamplingK,static_cast<UInt8>(0));
    GetNodeAttribute(tHierarchicalStructNode,"control",control);
    GetNodeAttribute(tHierarchicalStructNode,"voting_msgs",voting_msgs);
    GetNodeAttribute(tHierarchicalStructNode,"control_parameter",control_parameter);
    std::string strOptionsDistribution = "random";
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "options_distribution",strOptionsDistribution, strOptionsDistribution);
    g_strOptionsDistribution = NormalizeDistributionString(strOptionsDistribution);
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "spatial_correlation", m_fSpatialCorrelation, static_cast<Real>(0.0));
    eta_init = Min<Real>(1.0, Max<Real>(0.0, eta_init));
    eta_stop = Min<Real>(1.0, Max<Real>(0.0, eta_stop));
    variation_time = Max<uint16_t>(0,variation_time);
    options = Max<UInt8>(1, options);
    rebroadcast = Min<UInt8>(31, rebroadcast);
    msgs_n_hops = Min<UInt8>(31, msgs_n_hops);
    adaptive_comm = Min<UInt8>(1, adaptive_comm);
    m_unIdAware = Min<UInt8>(1, m_unIdAware);
    m_unhop_count = Min<UInt8>(1, m_unhop_count);
    m_unPrioritySamplingK = Min<UInt8>(127, m_unPrioritySamplingK);
    if(m_unIdAware == 0){
        rebroadcast = 0;
        msgs_n_hops = 0;
        adaptive_comm = 0;
    }
    if(rebroadcast == 0){
        adaptive_comm = 0;
    }
    voting_msgs = Min<UInt8>(127, voting_msgs);
    control_parameter = Min<Real>(1.0, Max<Real>(0.0, control_parameter));
    m_unControlMode = ControlModeFromString(control);
    m_unControlParameterQ = static_cast<UInt8>(std::round(control_parameter * 127.0));
    m_unEtaQ = static_cast<UInt8>(std::round(eta_init * 127.0));
    m_unFloorSeed = static_cast<UInt16>(m_random_seed & 0x0FFF);
    if(m_unFloorSeed == 0) {
        m_unFloorSeed = 1;
    }

    UInt32 unGridRows = 10;
    UInt32 unGridCols = 10;
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "grid_rows", unGridRows, unGridRows);
    GetNodeAttributeOrDefault(tHierarchicalStructNode, "grid_cols", unGridCols, unGridCols);

    m_cGridFloor.Rows = unGridRows;
    m_cGridFloor.Cols = unGridCols;
    if(m_cGridFloor.Rows > 0 && m_cGridFloor.Cols > 0) {
        const CVector3& cArenaMin = this->GetSpace().GetArenaLimits().GetMin();
        const CVector3& cArenaMax = this->GetSpace().GetArenaLimits().GetMax();
        
        m_fLimitMinX = cArenaMin.GetX() + 0.05;
        m_fLimitMinY = cArenaMin.GetY() + 0.05;
        m_fLimitMaxX = cArenaMax.GetX() - 0.05;
        m_fLimitMaxY = cArenaMax.GetY() - 0.05;

        const Real fCellSizeX = (m_fLimitMaxX - m_fLimitMinX) / m_cGridFloor.Cols;
        const Real fCellSizeY = (m_fLimitMaxY - m_fLimitMinY) / m_cGridFloor.Rows;

        m_cGridFloor.XMin = m_fLimitMinX;
        m_cGridFloor.YMin = m_fLimitMinY;
        m_cGridFloor.InvCellSizeX = (fCellSizeX > 0 ? 1.0 / fCellSizeX : 0);
        m_cGridFloor.InvCellSizeY = (fCellSizeY > 0 ? 1.0 / fCellSizeY : 0);
        m_cGridFloor.ColorId.assign(m_cGridFloor.Rows * m_cGridFloor.Cols, 1);
        
        SetupFloorColorMap();

        const Real fGpsMaxX = m_fLimitMaxX - m_fLimitMinX;
        const Real fGpsMaxY = m_fLimitMaxY - m_fLimitMinY;
        const SInt32 nGpsMaxXQ = static_cast<SInt32>(std::round(fGpsMaxX * 100.0));
        const SInt32 nGpsMaxYQ = static_cast<SInt32>(std::round(fGpsMaxY * 100.0));
        m_unGpsMaxXQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMaxXQ)));
        m_unGpsMaxYQ = static_cast<UInt8>(Min<SInt32>(127, Max<SInt32>(0, nGpsMaxYQ)));
    }
}

/****************************************/
/****************************************/
void CBestN_ALF::SetupFloorColorMap() {
    if (!m_bInitialFloorSetupAllowed && !m_bVariationFloorSetupAllowed) {
        return;
    }

    const UInt32 unTotalCells = m_cGridFloor.Rows * m_cGridFloor.Cols;
    if (unTotalCells == 0) {
        return;
    }

    /* 1. Calculate exact cell capacities based on floating-point eta */
    const Real fCurrentEta = (variation_time > 0 && m_fTimeInSeconds >= variation_time) ? eta_stop : eta_init;
    const UInt32 unWorseCells = static_cast<UInt32>(std::round(fCurrentEta * unTotalCells));
    const UInt32 unBestCells = unTotalCells - unWorseCells;

    struct SColorBucket {
        UInt8 ColorId;
        UInt32 TargetCount;
        UInt32 CurrentCount;
        Real SeedR;
        Real SeedC;
        Real WeightR;
        Real WeightC;
    };
    std::vector<SColorBucket> vecBuckets;

    /* Add best option (Color ID 1) */
    if (unBestCells > 0) {
        vecBuckets.push_back({ 1, unBestCells, 0, 0.0, 0.0, 1.0, 1.0 });
    }

    /* Add worse options (Color IDs 2 to options) */
    if (options > 1 && unWorseCells > 0) {
        const UInt8 unWorseOptions = options - 1;
        const UInt32 unBaseCount = unWorseCells / unWorseOptions;
        const UInt32 unRemainder = unWorseCells % unWorseOptions;

        for (UInt8 unOpt = 0; unOpt < unWorseOptions; ++unOpt) {
            const UInt32 unCellsForThisOption = unBaseCount + (unOpt < unRemainder ? 1 : 0);
            if (unCellsForThisOption > 0) {
                const UInt8 unColorId = static_cast<UInt8>((unOpt % 254) + 2);
                vecBuckets.push_back({ unColorId, unCellsForThisOption, 0, 0.0, 0.0, 1.0, 1.0 });
            }
        }
    }

    const size_t M = vecBuckets.size();
    if (M == 0) {
        return;
    }
    if (M == 1) {
        m_cGridFloor.ColorId.assign(unTotalCells, vecBuckets[0].ColorId);
        m_vecGridColors.resize(unTotalCells);
        for (UInt32 r = 0; r < m_cGridFloor.Rows; ++r) {
            for (UInt32 c = 0; c < m_cGridFloor.Cols; ++c) {
                m_vecGridColors[r * m_cGridFloor.Cols + c] = m_cGridFloor.GetColorAt(CVector2(0, 0));
            }
        }
        m_bInitialFloorSetupAllowed = false;
        m_bVariationFloorSetupAllowed = false;
        return;
    }

    /* 2. Generate well-separated random seeds and anisotropic stretch factors */
    std::mt19937 cLocalRNG(m_unFloorSeed);
    std::uniform_real_distribution<Real> cDistR(0.0, static_cast<Real>(m_cGridFloor.Rows));
    std::uniform_real_distribution<Real> cDistC(0.0, static_cast<Real>(m_cGridFloor.Cols));
    std::uniform_real_distribution<Real> cDistStretch(0.6, 1.8);

    const Real fMinDist = Min<Real>(static_cast<Real>(m_cGridFloor.Rows), static_cast<Real>(m_cGridFloor.Cols)) / static_cast<Real>(M + 1);
    const Real fMinDistSq = fMinDist * fMinDist;

    for (size_t m = 0; m < M; ++m) {
        Real fR = 0.0, fC = 0.0;
        bool bValid = false;
        for (UInt32 attempt = 0; attempt < 50; ++attempt) {
            fR = cDistR(cLocalRNG);
            fC = cDistC(cLocalRNG);
            bValid = true;
            for (size_t prev = 0; prev < m; ++prev) {
                Real dR = fR - vecBuckets[prev].SeedR;
                Real dC = fC - vecBuckets[prev].SeedC;
                if ((dR * dR + dC * dC) < fMinDistSq) {
                    bValid = false;
                    break;
                }
            }
            if (bValid) break;
        }
        vecBuckets[m].SeedR = fR;
        vecBuckets[m].SeedC = fC;
        vecBuckets[m].WeightR = cDistStretch(cLocalRNG);
        vecBuckets[m].WeightC = cDistStretch(cLocalRNG);
    }

    /* 3. Compute cell-to-seed affinities with spatial correlation and noise */
    struct SCellAffinity {
        UInt32 FlatIndex;
        UInt16 BucketIndex;
        Real Weight;
    };
    std::vector<SCellAffinity> vecAffinities;
    vecAffinities.reserve(unTotalCells * M);

    const Real fMaxDist = std::sqrt(static_cast<Real>(m_cGridFloor.Rows * m_cGridFloor.Rows + m_cGridFloor.Cols * m_cGridFloor.Cols));
    const Real fAlpha = Min<Real>(1.0, Max<Real>(0.0, m_fSpatialCorrelation));
    std::uniform_real_distribution<Real> cDistNoise(0.0, 1.0);

    for (UInt32 r = 0; r < m_cGridFloor.Rows; ++r) {
        for (UInt32 c = 0; c < m_cGridFloor.Cols; ++c) {
            const UInt32 unFlatIndex = r * m_cGridFloor.Cols + c;
            const Real fCellR = static_cast<Real>(r) + 0.5;
            const Real fCellC = static_cast<Real>(c) + 0.5;

            for (size_t m = 0; m < M; ++m) {
                const Real dR = fCellR - vecBuckets[m].SeedR;
                const Real dC = fCellC - vecBuckets[m].SeedC;
                const Real fDist = std::sqrt(vecBuckets[m].WeightR * dR * dR + vecBuckets[m].WeightC * dC * dC) / fMaxDist;
                
                const Real fNoise = cDistNoise(cLocalRNG);
                /* 
                 * Alpha=0: Pure random noise (uniform random scatter).
                 * Alpha=1: Anisotropic distance + 8% noise (jagged, squished organic patches).
                 */
                const Real fWeight = fAlpha * fDist + (1.0 - 0.92 * fAlpha) * fNoise;

                vecAffinities.push_back({ unFlatIndex, static_cast<UInt16>(m), fWeight });
            }
        }
    }

    /* 4. Capacitated greedy assignment by minimum affinity weight */
    std::sort(vecAffinities.begin(), vecAffinities.end(), [](const SCellAffinity& a, const SCellAffinity& b) {
        return a.Weight < b.Weight;
    });

    m_cGridFloor.ColorId.assign(unTotalCells, 1);
    std::vector<bool> vecAssigned(unTotalCells, false);
    UInt32 unTotalAssigned = 0;

    for (const auto& aff : vecAffinities) {
        if (!vecAssigned[aff.FlatIndex] && vecBuckets[aff.BucketIndex].CurrentCount < vecBuckets[aff.BucketIndex].TargetCount) {
            vecAssigned[aff.FlatIndex] = true;
            m_cGridFloor.ColorId[aff.FlatIndex] = vecBuckets[aff.BucketIndex].ColorId;
            vecBuckets[aff.BucketIndex].CurrentCount++;
            unTotalAssigned++;
            if (unTotalAssigned == unTotalCells) {
                break;
            }
        }
    }

    /* 5. Render floor colour vector for simulation visualisation */
    m_vecGridColors.resize(unTotalCells);
    for (UInt32 r = 0; r < m_cGridFloor.Rows; ++r) {
        for (UInt32 c = 0; c < m_cGridFloor.Cols; ++c) {
            CVector2 cCellCenter(
                m_fLimitMinX + (c + 0.5) / m_cGridFloor.InvCellSizeX,
                m_fLimitMinY + (r + 0.5) / m_cGridFloor.InvCellSizeY
            );
            m_vecGridColors[r * m_cGridFloor.Cols + c] = m_cGridFloor.GetColorAt(cCellCenter);
        }
    }

    m_bInitialFloorSetupAllowed = false;
    m_bVariationFloorSetupAllowed = false;
}

/****************************************/
/****************************************/

void CBestN_ALF::GetExperimentVariables(TConfigurationNode& t_tree){
    /* Get the experiment variables node from the .argos file */
    TConfigurationNode& tExperimentVariablesNode = GetNode(t_tree,"variables");
    /* Get the output datafile name and open it */
    GetNodeAttribute(tExperimentVariablesNode, "logfilename", m_strLogFileName);
    /* Get the frequency of data saving */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "dataacquisitionfrequency", m_unDataAcquisitionFrequency, m_unDataAcquisitionFrequency);
    /* Get the frequency of updating the environment plot */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "m_unEnvironmentPlotUpdateFrequency", m_unEnvironmentPlotUpdateFrequency, m_unEnvironmentPlotUpdateFrequency);
    /* Get the time for one kilobot message */
    GetNodeAttributeOrDefault(tExperimentVariablesNode, "timeforonemessage", m_fTimeForAMessage, m_fTimeForAMessage);
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateKilobotState(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::UpdateVirtualSensor(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    if (m_fTimeInSeconds - m_vecLastTimeMessaged[unKilobotID]< m_fMinTimeBetweenTwoMsg) return; // if the time is too short, the kilobot cannot receive a message
    for (UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i]=0; // clear all the variables used for messaging
    switch (start_experiment){
        case 0:
            /* Send init information for environment representation*/
            switch (m_vecStart_experiment[unKilobotID]){
                case 0:
                    m_vecStart_experiment[unKilobotID]=1;
                    SendStructInitInformation(c_kilobot_entity);
                    break;
                case 1:
                    m_vecStart_experiment[unKilobotID]=2;
                    SendBufferInitInformation(c_kilobot_entity);
                    break;
                case 2:
                    m_vecStart_experiment[unKilobotID]=3;
                    SendBoundsInitInformation(c_kilobot_entity);
                    break;
                case 3:
                    m_vecStart_experiment[unKilobotID]=4;
                    SendStateInformation(c_kilobot_entity);
                    break;
                case 4:
                    m_vecStart_experiment[unKilobotID]=5;
                    SendInformationGPS(c_kilobot_entity);
                    break;
            }
            start_experiment=1;
            for(size_t i = 0; i < m_vecStart_experiment.size(); ++i){
                if(m_vecStart_experiment[i]!=5){
                    start_experiment=0;
                    break;
                }
            }
            break;
        default:
            SendInformationGPS(c_kilobot_entity);
            break;
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SendStructInitInformation(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    m_tMessages[unKilobotID].type = 0;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    const UInt16 unPayload = msgs_timeout & 0x3FFFu;
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    const UInt8 unPacketData = static_cast<UInt8>(((adaptive_comm & 0x01u) << 5) | (rebroadcast & 0x1Fu));
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>((0u << 6) | (unPacketData & 0x3Fu));
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendBufferInitInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    m_tMessages[unKilobotID].type = 0;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    const UInt16 unPayload = static_cast<UInt16>(
        (m_unPrioritySamplingK & 0x7Fu) |
        ((m_unIdAware & 0x01u) << 7) |
        ((m_unhop_count & 0x01u) << 8));
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(2u << 6);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendBoundsInitInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;

    m_tMessages[unKilobotID].type = 0;
    const UInt16 unPayload = static_cast<UInt16>(((m_unGpsMaxXQ & 0x7Fu) << 7) | (m_unGpsMaxYQ & 0x7Fu));
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 7) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(3u << 6);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/
void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    m_tMessages[unKilobotID].type = 1;
    for(UInt8 i = 0; i < 9; ++i) {
        m_tMessages[unKilobotID].data[i] = 0;
    }

    const Real fAngleDeg = m_vecKilobotOrientations[unKilobotID].GetValue();
    UInt8 unAngleQ = static_cast<UInt8>(std::floor(fAngleDeg * (256.0 / 360.0))) & 0xFFu;
    const Real fPosXInRobotFrame = m_vecKilobotPositions[unKilobotID].GetX() - m_cGridFloor.XMin;
    const Real fPosYInRobotFrame = m_vecKilobotPositions[unKilobotID].GetY() - m_cGridFloor.YMin;
    const SInt32 nXQ = static_cast<SInt32>(std::round(fPosXInRobotFrame * 50.0));
    const SInt32 nYQ = static_cast<SInt32>(std::round(fPosYInRobotFrame * 50.0));
    UInt8 unXQ = static_cast<UInt8>(Min<SInt32>(63, Max<SInt32>(0, nXQ)));
    UInt8 unYQ = static_cast<UInt8>(Min<SInt32>(63, Max<SInt32>(0, nYQ)));

    UInt8 unColorId = m_cGridFloor.GetColorIdAt(m_vecKilobotPositions[unKilobotID]);
    UInt8 unColorQ = 0;
    if(unColorId > 0 && unColorId < 255) {
        unColorQ = static_cast<UInt8>((unColorId - 1) % 6);
    }

    const UInt32 unPayload =
        (static_cast<UInt32>(unXQ) & 0x3Fu) |
        ((static_cast<UInt32>(unYQ) & 0x3Fu) << 6) |
        ((static_cast<UInt32>(unAngleQ) & 0xFFu) << 12) |
        ((static_cast<UInt32>(unColorQ) & 0x07u) << 20);

    /* Individual GPS packet: MSG_A in bit0 + 23-bit payload across 3 bytes. */
    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>(((unPayload >> 16) & 0x7Fu) << 1);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>((unPayload >> 8) & 0xFFu);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(unPayload & 0xFFu);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/
void CBestN_ALF::SendStateInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;

    m_tMessages[unKilobotID].type = 1;
    for(UInt8 i = 0; i < 9; ++i) m_tMessages[unKilobotID].data[i] = 0;

    const UInt8 unKilobotId7b = static_cast<UInt8>(unKilobotID & 0x7Fu);
    const UInt16 unPayloadHops = static_cast<UInt16>(msgs_n_hops & 0x1Fu);
    
    const UInt16 unPayloadControl = static_cast<UInt16>(
        ((m_unControlMode & 0x03u) << 14) |
        ((voting_msgs & 0x7Fu) << 7) |
        (m_vecKilobotState[unKilobotID] & 0x7Fu));

    m_tMessages[unKilobotID].data[0] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[1] = static_cast<UInt8>(unPayloadHops >> 8);
    m_tMessages[unKilobotID].data[2] = static_cast<UInt8>(unPayloadHops & 0xFFu);

    m_tMessages[unKilobotID].data[3] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[4] = static_cast<UInt8>(unPayloadControl >> 8);
    m_tMessages[unKilobotID].data[5] = static_cast<UInt8>(unPayloadControl & 0xFFu);

    m_tMessages[unKilobotID].data[6] = static_cast<UInt8>((unKilobotId7b << 1) | 0x01u);
    m_tMessages[unKilobotID].data[7] = 0;
    m_tMessages[unKilobotID].data[8] = static_cast<UInt8>(m_unControlParameterQ & 0x7Fu);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

CColor CBestN_ALF::GetFloorColor(const CVector2 &vec_position_on_plane){
    const Real fX = vec_position_on_plane.GetX();
    const Real fY = vec_position_on_plane.GetY();
    if(fX < m_fLimitMinX || fX > m_fLimitMaxX || fY < m_fLimitMinY || fY > m_fLimitMaxY) {
        return CColor::BLACK;
    }
    UInt32 c = static_cast<UInt32>((fX - m_fLimitMinX) * m_cGridFloor.InvCellSizeX);
    UInt32 r = static_cast<UInt32>((fY - m_fLimitMinY) * m_cGridFloor.InvCellSizeY);
    if (c >= static_cast<UInt32>(m_cGridFloor.Cols)) c = m_cGridFloor.Cols - 1;
    if (r >= static_cast<UInt32>(m_cGridFloor.Rows)) r = m_cGridFloor.Rows - 1;
    return m_vecGridColors[r * m_cGridFloor.Cols + c];
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")