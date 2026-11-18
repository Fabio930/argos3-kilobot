/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#include "BestN_ALF.h"
#include <argos3/plugins/robots/kilobot/simulator/kilobot_measures.h>
#include <algorithm>
#include <cctype>
#include <cmath>

namespace {

UInt16 ComputeCommittedCount(float fPercentage, UInt16 unNumKilobots) {
    const double fClampedPercentage = std::max(0.0, std::min(1.0, static_cast<double>(fPercentage)));
    SInt32 nTargetCommitted = static_cast<SInt32>(std::llround(fClampedPercentage * static_cast<double>(unNumKilobots)));
    nTargetCommitted = std::max<SInt32>(0, std::min<SInt32>(nTargetCommitted, unNumKilobots));
    return static_cast<UInt16>(nTargetCommitted);
}

std::string ToLower(std::string str) {
    std::transform(str.begin(), str.end(), str.begin(), [](unsigned char c){ return std::tolower(c); });
    return str;
}

bool ParseBool(const std::string& str_value, const std::string& str_name) {
    const std::string strLower = ToLower(str_value);
    if(strLower == "true" || strLower == "1" || strLower == "yes") return true;
    if(strLower == "false" || strLower == "0" || strLower == "no") return false;
    THROW_ARGOSEXCEPTION("hierarchicStruct: '" << str_name << "' must be true or false, got '" << str_value << "'");
}

template<typename T>
T ReadRequired(TConfigurationNode& t_node, const std::string& str_name, const std::string& str_reason) {
    if(!NodeAttributeExists(t_node, str_name))
        THROW_ARGOSEXCEPTION("hierarchicStruct: missing attribute '" << str_name << "' (" << str_reason << ")");
    T tValue;
    GetNodeAttribute(t_node, str_name, tValue);
    return tValue;
}

void WriteU16(UInt8* pt_data, UInt16 un_value) {
    pt_data[0] = static_cast<UInt8>(un_value >> 8);
    pt_data[1] = static_cast<UInt8>(un_value & 0x00FF);
}

UInt16 ToCentimeters(Real f_meters) {
    return static_cast<UInt16>(std::max<long>(0, std::lround(f_meters * 100.0)));
}

}

/****************************************/
/****************************************/

CBestN_ALF::CBestN_ALF() :
    anonymous_comm(false),
    dynamic_env(false),
    confined_env(false),
    committed_percentage(0),
    quorum_threshold(0.8),
    expiring_quorum_sec(0),
    msgs_n_hops(0),
    rebroadcast(0),
    hop_count(0),
    queue_lenght(0),
    k_sampling(0),
    start_commitment_variation_time(0),
    end_commitment_variation_time(0),
    next_committed_percentage(0),
    middle_x_area(0),
    m_unDataAcquisitionFrequency(10){
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
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotStates(){
    const UInt16 unNumKilobots = m_tKilobotEntities.size();
    UInt16 unMaxID = 0;
    std::vector<UInt16> vecKilobotIDs(unNumKilobots);
    for(UInt16 it = 0; it < unNumKilobots; ++it){
        vecKilobotIDs[it] = GetKilobotId(*m_tKilobotEntities[it]);
        unMaxID = std::max(unMaxID, vecKilobotIDs[it]);
    }
    /* robot IDs travel in one byte, 255 is never used */
    if(unMaxID > 254) THROW_ARGOSEXCEPTION("BestN: kilobot IDs must be at most 254 (found " << unMaxID << ")");
    /* messages and per-robot vectors are indexed by ID */
    if(unNumKilobots > 0 && unMaxID >= unNumKilobots) THROW_ARGOSEXCEPTION("BestN: kilobot IDs must be 0.." << unNumKilobots-1 << " (found " << unMaxID << ")");
    if(anonymous_comm && unNumKilobots > 0 && queue_lenght == 0) THROW_ARGOSEXCEPTION("BestN: queue_lenght must be at least 1");

    const UInt16 unVecSize = unMaxID + 1;
    m_vecKilobotMsgType.assign(unVecSize, 0);
    m_vecLastTimeMessaged.assign(unVecSize, 0);
    m_vecStart_experiment.assign(unVecSize, 0);
    m_vecKilobotPositions.resize(unVecSize);
    m_vecKilobotOrientations.resize(unVecSize);
    m_vecKilobotStates.assign(unVecSize, 0);
    m_vecVariationSeeds.assign(unVecSize, 0);
    m_vecVariationNumFlips.assign(unVecSize, 0);
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, unNumKilobots * m_fTimeForAMessage / 3.0);

    /* exact share of committed robots, chosen at random (seeded by the experiment seed) */
    std::vector<UInt16> vecShuffled = vecKilobotIDs;
    for(UInt16 it = unNumKilobots; it > 1; --it){
        std::swap(vecShuffled[it - 1], vecShuffled[c_rng->Uniform(CRange<UInt32>(0, it))]);
    }
    std::vector<UInt8> assigned_kilo_states(unVecSize, 0); /* indexed by kilobot ID */
    const UInt16 unInitialCommitted = ComputeCommittedCount(committed_percentage, unNumKilobots);
    for(UInt16 it = 0; it < unInitialCommitted; ++it) assigned_kilo_states[vecShuffled[it]] = 1;

    if(dynamic_env) SetupStateVariationPlan(assigned_kilo_states);
    if(confined_env) PlaceConfinedKilobots(assigned_kilo_states);

    for(UInt16 it = 0; it < unNumKilobots; ++it){
        SetupInitialKilobotState(*m_tKilobotEntities[it], assigned_kilo_states[vecKilobotIDs[it]]);
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity,UInt8 state){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotMsgType[unKilobotID] = 0;
    m_vecKilobotStates[unKilobotID] = state;
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupStateVariationPlan(const std::vector<UInt8>& vec_assigned_states){
    /* robots that change state an odd number of times produce the target share at the end of the window */
    std::vector<UInt16> vecCommitted;
    std::vector<UInt16> vecUncommitted;
    std::vector<UInt16> vecIDs;
    for(UInt16 it = 0; it < m_tKilobotEntities.size(); ++it){
        const UInt16 unID = GetKilobotId(*m_tKilobotEntities[it]);
        vecIDs.push_back(unID);
        if(vec_assigned_states[unID] == 1) vecCommitted.push_back(unID);
        else vecUncommitted.push_back(unID);
    }
    const SInt32 nTargetCommitted = static_cast<SInt32>(ComputeCommittedCount(next_committed_percentage, vecIDs.size()));
    const SInt32 nDeltaCommitted = nTargetCommitted - static_cast<SInt32>(vecCommitted.size());
    const bool bAbruptVariation = (end_commitment_variation_time == 0 || end_commitment_variation_time <= start_commitment_variation_time);

    std::vector<UInt16> vecCandidates = (nDeltaCommitted >= 0) ? vecUncommitted : vecCommitted;
    for(UInt16 it = vecCandidates.size(); it > 1; --it){
        std::swap(vecCandidates[it - 1], vecCandidates[c_rng->Uniform(CRange<UInt32>(0, it))]);
    }
    std::vector<UInt8> vecNeedsOdd(vec_assigned_states.size(), 0);
    UInt16 unOddCount = static_cast<UInt16>(std::abs(nDeltaCommitted));
    if(unOddCount > vecCandidates.size()) unOddCount = vecCandidates.size();
    for(UInt16 it = 0; it < unOddCount; ++it) vecNeedsOdd[vecCandidates[it]] = 1;

    for(UInt16 unID : vecIDs){
        UInt8 unNumFlips;
        if(vecNeedsOdd[unID]) unNumFlips = bAbruptVariation ? 1 : static_cast<UInt8>(2 * c_rng->Uniform(CRange<UInt32>(0, 5)) + 1);
        else unNumFlips = bAbruptVariation ? 0 : static_cast<UInt8>(2 * c_rng->Uniform(CRange<UInt32>(0, 5)));
        m_vecVariationNumFlips[unID] = unNumFlips;
        m_vecVariationSeeds[unID] = static_cast<UInt16>(c_rng->Uniform(CRange<UInt32>(1, 0x10000)));
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::PlaceConfinedKilobots(const std::vector<UInt8>& vec_assigned_states){
    const CVector3& cArenaMin = GetSpace().GetArenaLimits().GetMin();
    const CVector3& cArenaMax = GetSpace().GetArenaLimits().GetMax();
    const Real fBorder = ARENA_BORDER_M;
    const Real fRadius = KILOBOT_RADIUS;
    std::vector<CVector2> vecPlaced;
    for(UInt16 it = 0; it < m_tKilobotEntities.size(); ++it){
        CKilobotEntity& cKilobot = *m_tKilobotEntities[it];
        const UInt16 unID = GetKilobotId(cKilobot);
        Real fMinX, fMaxX;
        if(vec_assigned_states[unID] == 1){
            fMinX = cArenaMin.GetX() + fBorder + fRadius;
            fMaxX = middle_x_area - fRadius;
        }
        else{
            fMinX = middle_x_area + fRadius;
            fMaxX = cArenaMax.GetX() - fBorder - fRadius;
        }
        const Real fMinY = cArenaMin.GetY() + fBorder + fRadius;
        const Real fMaxY = cArenaMax.GetY() - fBorder - fRadius;
        if(fMinX >= fMaxX || fMinY >= fMaxY) THROW_ARGOSEXCEPTION("BestN: middle_x_area=" << middle_x_area << " leaves no room for the robots");
        const CQuaternion cOrientation(GetKilobotOrientation(cKilobot), CVector3::Z);
        bool bPlaced = false;
        for(UInt32 trial = 0; trial < 100000 && !bPlaced; ++trial){
            const CVector2 cCandidate(c_rng->Uniform(CRange<Real>(fMinX, fMaxX)), c_rng->Uniform(CRange<Real>(fMinY, fMaxY)));
            bool bOverlap = false;
            for(const CVector2& cOther : vecPlaced){
                if(Abs(cCandidate.GetX() - cOther.GetX()) <= 2*fRadius + 0.005 && Abs(cCandidate.GetY() - cOther.GetY()) <= 2*fRadius + 0.005){
                    bOverlap = true;
                    break;
                }
            }
            if(bOverlap) continue;
            if(cKilobot.GetEmbodiedEntity().MoveTo(CVector3(cCandidate.GetX(), cCandidate.GetY(), 0), cOrientation)){
                vecPlaced.push_back(cCandidate);
                bPlaced = true;
            }
        }
        if(!bPlaced) THROW_ARGOSEXCEPTION("BestN: too many robots to place in the confined areas");
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupVirtualEnvironments(TConfigurationNode& t_tree){
    CSimulator &simulator = GetSimulator();
    m_random_seed = simulator.GetRandomSeed();
    TConfigurationNode& tNode = GetNode(t_tree,"hierarchicStruct");

    /* variant selectors */
    std::string strValue;
    GetNodeAttributeOrDefault<std::string>(tNode, "communication", strValue, "id");
    strValue = ToLower(strValue);
    if(strValue == "id") anonymous_comm = false;
    else if(strValue == "anonymous") anonymous_comm = true;
    else THROW_ARGOSEXCEPTION("hierarchicStruct: 'communication' must be id or anonymous, got '" << strValue << "'");
    GetNodeAttributeOrDefault<std::string>(tNode, "dynamic", strValue, "false");
    dynamic_env = ParseBool(strValue, "dynamic");
    GetNodeAttributeOrDefault<std::string>(tNode, "confined", strValue, "false");
    confined_env = ParseBool(strValue, "confined");
    if(dynamic_env && confined_env)
        THROW_ARGOSEXCEPTION("hierarchicStruct: dynamic=\"true\" and confined=\"true\" cannot be used together");

    /* common parameters */
    const UInt32 unRebroadcast = ReadRequired<UInt32>(tNode, "rebroadcast", "rebroadcast policy 0, 1 or 2");
    if(unRebroadcast > 2) THROW_ARGOSEXCEPTION("hierarchicStruct: 'rebroadcast' must be 0, 1 or 2");
    rebroadcast = unRebroadcast;
    committed_percentage = ReadRequired<float>(tNode, "committed_percentage", "share of committed robots");
    if(committed_percentage < 0 || committed_percentage > 1) THROW_ARGOSEXCEPTION("hierarchicStruct: 'committed_percentage' must be in [0,1]");
    UInt32 unExpiring;
    if(NodeAttributeExists(tNode, "expiring_quorum_sec")) GetNodeAttribute(tNode, "expiring_quorum_sec", unExpiring);
    else unExpiring = ReadRequired<UInt32>(tNode, "msg_expiring_seconds", "message expiring time in seconds (alias of expiring_quorum_sec)");
    if(unExpiring > 0xFFFF) THROW_ARGOSEXCEPTION("hierarchicStruct: 'expiring_quorum_sec' must be at most 65535");
    expiring_quorum_sec = unExpiring;
    UInt32 unHops;
    GetNodeAttributeOrDefault<UInt32>(tNode, "msgs_n_hops", unHops, 0);
    if(unHops > 255) THROW_ARGOSEXCEPTION("hierarchicStruct: 'msgs_n_hops' must be at most 255");
    msgs_n_hops = unHops;
    UInt32 unHopCount;
    GetNodeAttributeOrDefault<UInt32>(tNode, "hop_count", unHopCount, 0);
    if(unHopCount > 1) THROW_ARGOSEXCEPTION("hierarchicStruct: 'hop_count' must be 0 or 1");
    hop_count = unHopCount;
    GetNodeAttributeOrDefault<float>(tNode, "quorum_threshold", quorum_threshold, 0.8);
    if(quorum_threshold < 0 || quorum_threshold > 1) THROW_ARGOSEXCEPTION("hierarchicStruct: 'quorum_threshold' must be in [0,1]");

    /* anonymous communication */
    if(anonymous_comm){
        if(rebroadcast != 0) THROW_ARGOSEXCEPTION("hierarchicStruct: anonymous robots never rebroadcast, set rebroadcast=\"0\"");
        const UInt32 unQueue = ReadRequired<UInt32>(tNode, "queue_lenght", "buffer length of the anonymous communication");
        if(unQueue < 1 || unQueue > 255) THROW_ARGOSEXCEPTION("hierarchicStruct: 'queue_lenght' must be in [1,255]");
        queue_lenght = unQueue;
        UInt32 unK;
        GetNodeAttributeOrDefault<UInt32>(tNode, "k_sampling", unK, 0);
        if(unK > 255) THROW_ARGOSEXCEPTION("hierarchicStruct: 'k_sampling' must be at most 255");
        k_sampling = unK;
    }

    /* dynamic environment */
    if(dynamic_env){
        const UInt32 unStart = ReadRequired<UInt32>(tNode, "start_commitment_variation_time", "dynamic=true");
        UInt32 unEnd;
        GetNodeAttributeOrDefault<UInt32>(tNode, "end_commitment_variation_time", unEnd, 0);
        if(unStart > 0xFFFF || unEnd > 0xFFFF) THROW_ARGOSEXCEPTION("hierarchicStruct: variation times must be at most 65535 s");
        start_commitment_variation_time = unStart;
        end_commitment_variation_time = unEnd;
        next_committed_percentage = ReadRequired<float>(tNode, "next_committed_percentage", "dynamic=true");
        if(next_committed_percentage < 0 || next_committed_percentage > 1) THROW_ARGOSEXCEPTION("hierarchicStruct: 'next_committed_percentage' must be in [0,1]");
    }

    /* confined environment */
    if(confined_env){
        middle_x_area = ReadRequired<Real>(tNode, "middle_x_area", "confined=true");
        const CVector3& cMin = GetSpace().GetArenaLimits().GetMin();
        const CVector3& cMax = GetSpace().GetArenaLimits().GetMax();
        if(middle_x_area <= cMin.GetX() || middle_x_area >= cMax.GetX())
            THROW_ARGOSEXCEPTION("hierarchicStruct: 'middle_x_area' must be inside the arena (" << cMin.GetX() << ", " << cMax.GetX() << ")");
    }

    m_vecInitSequence = {ALF_MSG_CONFIG, ALF_MSG_STATE, ALF_MSG_ARENA};
    if(dynamic_env) m_vecInitSequence.push_back(ALF_MSG_VARIATION);
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
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    if (m_fTimeInSeconds - m_vecLastTimeMessaged[unKilobotID] < m_fMinTimeBetweenTwoMsg) return; // the kilobot cannot receive a message yet
    UInt8& unStep = m_vecStart_experiment[unKilobotID];
    if(unStep < m_vecInitSequence.size()){
        switch(m_vecInitSequence[unStep]){
            case ALF_MSG_CONFIG:    SendConfigInformation(c_kilobot_entity);    break;
            case ALF_MSG_STATE:     SendStateInformation(c_kilobot_entity);     break;
            case ALF_MSG_ARENA:     SendArenaInformation(c_kilobot_entity);     break;
            case ALF_MSG_VARIATION: SendVariationInformation(c_kilobot_entity); break;
        }
        unStep++;
    }
    else SendInformationGPS(c_kilobot_entity);
}

/****************************************/
/****************************************/

message_t& CBestN_ALF::PrepareMessage(UInt16 un_kilobot_id, UInt8 un_kind, UInt8 un_type){
    message_t& tMessage = m_tMessages[un_kilobot_id];
    for (UInt8 i = 0; i < 9; ++i) tMessage.data[i] = 0;
    tMessage.type = un_type;
    tMessage.data[0] = static_cast<UInt8>(un_kilobot_id);
    tMessage.data[1] = un_kind;
    return tMessage;
}

void CBestN_ALF::Deliver(CKilobotEntity &c_kilobot_entity, UInt16 un_kilobot_id){
    m_vecLastTimeMessaged[un_kilobot_id] = m_fTimeInSeconds;
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[un_kilobot_id]);
}

void CBestN_ALF::SendConfigInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    message_t& tMessage = PrepareMessage(unKilobotID, ALF_MSG_CONFIG, 0);
    UInt8 unFlags = 0;
    if(anonymous_comm) unFlags |= CFG_FLAG_ANONYMOUS;
    if(dynamic_env) unFlags |= CFG_FLAG_DYNAMIC;
    if(confined_env) unFlags |= CFG_FLAG_CONFINED;
    if(hop_count) unFlags |= CFG_FLAG_HOP_COUNT;
    tMessage.data[2] = unFlags;
    tMessage.data[3] = rebroadcast;
    WriteU16(&tMessage.data[4], expiring_quorum_sec);
    tMessage.data[6] = msgs_n_hops;
    tMessage.data[7] = static_cast<UInt8>(queue_lenght);
    tMessage.data[8] = k_sampling;
    Deliver(c_kilobot_entity, unKilobotID);
}

void CBestN_ALF::SendStateInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    message_t& tMessage = PrepareMessage(unKilobotID, ALF_MSG_STATE, 0);
    tMessage.data[2] = m_vecKilobotStates[unKilobotID];
    tMessage.data[3] = static_cast<UInt8>(std::lround(quorum_threshold * 100.0));
    Deliver(c_kilobot_entity, unKilobotID);
}

void CBestN_ALF::SendArenaInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    message_t& tMessage = PrepareMessage(unKilobotID, ALF_MSG_ARENA, 0);
    const CVector3& cArenaMax = GetSpace().GetArenaLimits().GetMax();
    /* robot frame: x_robot = x_world + arena_max_x */
    WriteU16(&tMessage.data[2], ToCentimeters(2 * cArenaMax.GetX()));
    WriteU16(&tMessage.data[4], ToCentimeters(2 * cArenaMax.GetY()));
    WriteU16(&tMessage.data[6], confined_env ? ToCentimeters(middle_x_area + cArenaMax.GetX()) : ARENA_NO_MIDLINE);
    Deliver(c_kilobot_entity, unKilobotID);
}

void CBestN_ALF::SendVariationInformation(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    message_t& tMessage = PrepareMessage(unKilobotID, ALF_MSG_VARIATION, 0);
    WriteU16(&tMessage.data[2], start_commitment_variation_time);
    WriteU16(&tMessage.data[4], end_commitment_variation_time);
    WriteU16(&tMessage.data[6], m_vecVariationSeeds[unKilobotID]);
    tMessage.data[8] = m_vecVariationNumFlips[unKilobotID];
    Deliver(c_kilobot_entity, unKilobotID);
}

void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity){
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    message_t& tMessage = PrepareMessage(unKilobotID, ALF_MSG_GPS, 1);
    const CVector3& cArenaMax = GetSpace().GetArenaLimits().GetMax();
    /* same quantisation as the original encoding: 2 cm and 24 degrees */
    const Real fX = std::max<Real>(0, m_vecKilobotPositions[unKilobotID].GetX() + cArenaMax.GetX());
    const Real fY = std::max<Real>(0, m_vecKilobotPositions[unKilobotID].GetY() + cArenaMax.GetY());
    const UInt16 unX = static_cast<UInt16>(static_cast<UInt32>(fX * 100) / 2);
    const UInt16 unY = static_cast<UInt16>(static_cast<UInt32>(fY * 100) / 2);
    WriteU16(&tMessage.data[2], unX);
    WriteU16(&tMessage.data[4], unY);
    tMessage.data[6] = static_cast<UInt8>(m_vecKilobotOrientations[unKilobotID].GetValue() * 0.0417);
    Deliver(c_kilobot_entity, unKilobotID);
}

/****************************************/
/****************************************/

Real CBestN_ALF::abs_distance(const CVector2 a, const CVector2 b){
    Real x = a.GetX()-b.GetX();
    x = x * x;
    Real y = a.GetY()-b.GetY();
    y = y * y;
    return sqrt(x + y);
}

/****************************************/
/****************************************/

CColor CBestN_ALF::GetFloorColor(const CVector2 &vec_position_on_plane){
    CColor color=CColor::WHITE;
    if(abs(vec_position_on_plane.GetX())>this->GetSpace().GetArenaLimits().GetMax()[0]-ARENA_BORDER_M || abs(vec_position_on_plane.GetY())>this->GetSpace().GetArenaLimits().GetMax()[1]-ARENA_BORDER_M) color=CColor::BLACK;
    else if(confined_env && vec_position_on_plane.GetX() < middle_x_area) color=CColor::GREEN;
    return color;
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
