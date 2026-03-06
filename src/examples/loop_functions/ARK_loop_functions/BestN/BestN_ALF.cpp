/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/

#include "BestN_ALF.h"
#include <algorithm>
#include <cmath>

namespace {

constexpr UInt16 VARIATION_START_TAG = 0xA000;
constexpr UInt16 VARIATION_END_TAG = 0xB000;
constexpr UInt16 VARIATION_TIME_MASK = 0x0FFF;

UInt16 ComputeCommittedCount(float fPercentage, UInt16 unNumKilobots) {
    const double fClampedPercentage = std::max(0.0, std::min(1.0, static_cast<double>(fPercentage)));
    SInt32 nTargetCommitted = static_cast<SInt32>(std::llround(fClampedPercentage * static_cast<double>(unNumKilobots)));
    nTargetCommitted = std::max<SInt32>(0, std::min<SInt32>(nTargetCommitted, unNumKilobots));
    return static_cast<UInt16>(nTargetCommitted);
}

void PrepareSimpleIndividualMSG(message_t& tMessage, UInt16 unKilobotID, UInt16 unPayload) {
    for(UInt8 i = 0; i < 9; ++i) tMessage.data[i] = 0;
    tMessage.type = 1;
    tMessage.data[0] = static_cast<UInt8>((unKilobotID << 1) | 0b00000001);
    tMessage.data[1] = static_cast<UInt8>(unPayload >> 8);
    tMessage.data[2] = static_cast<UInt8>(unPayload & 0x00FF);
    tMessage.data[3] = 0b11111110;
    tMessage.data[6] = 0b11111110;
}

}

/****************************************/
/****************************************/

CBestN_ALF::CBestN_ALF() :
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
    m_vecKilobotMsgType.resize(unNumKilobots);
    m_vecLastTimeMessaged.resize(unNumKilobots);
    m_vecStart_experiment.resize(unNumKilobots);
    m_vecKilobotPositions.resize(unNumKilobots);
    m_vecKilobotOrientations.resize(unNumKilobots);
    m_vecKilobotStates.resize(unNumKilobots);
    m_vecVariationSeeds.resize(unNumKilobots);
    m_vecVariationNumFlips.resize(unNumKilobots);
    m_fMinTimeBetweenTwoMsg = Max<Real>(1.0, unNumKilobots * m_fTimeForAMessage / 3.0);
    /* Setup the virtual states of a kilobot */
    std::vector<UInt8> assigned_kilo_states(unNumKilobots, 0); /* indexed by kilobot ID */
    std::vector<UInt16> vecKilobotIDs(unNumKilobots);
    for(UInt16 it = 0; it < unNumKilobots; ++it){
        vecKilobotIDs[it] = GetKilobotId(*m_tKilobotEntities[it]);
    }
    for(UInt16 it = unNumKilobots; it > 1; --it){
        std::swap(vecKilobotIDs[it - 1], vecKilobotIDs[rand() % it]);
    }
    const UInt16 unInitialCommittedTarget = ComputeCommittedCount(committed_percentage, unNumKilobots);
    for(UInt16 it = 0; it < unInitialCommittedTarget; ++it){
        assigned_kilo_states[vecKilobotIDs[it]] = 1;
    }
    
    SetupStateVariationPlan(assigned_kilo_states);
    for(UInt16 it = 0; it < unNumKilobots; ++it){
        const UInt16 unKilobotID = GetKilobotId(*m_tKilobotEntities[it]);
        SetupInitialKilobotState(*m_tKilobotEntities[it], assigned_kilo_states[unKilobotID]);
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupInitialKilobotState(CKilobotEntity &c_kilobot_entity,UInt8 state){
    /* The kilobots begins in the root node with a random goal position inside it */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecKilobotMsgType[unKilobotID] = 0;
    m_vecKilobotStates[unKilobotID] = state;
    m_vecKilobotPositions[unKilobotID] = GetKilobotPosition(c_kilobot_entity);
    m_vecKilobotOrientations[unKilobotID] = ToDegrees(GetKilobotOrientation(c_kilobot_entity)).UnsignedNormalize();
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupStateVariationPlan(const std::vector<UInt8>& vec_assigned_states){
    const UInt16 unNumKilobots = vec_assigned_states.size();
    std::vector<UInt16> vecCommitted;
    std::vector<UInt16> vecUncommitted;
    vecCommitted.reserve(unNumKilobots);
    vecUncommitted.reserve(unNumKilobots);
    UInt16 unInitialCommitted = 0;

    for(UInt16 it = 0; it < unNumKilobots; ++it){
        if(vec_assigned_states[it] == 1){
            ++unInitialCommitted;
            vecCommitted.push_back(it);
        }
        else{
            vecUncommitted.push_back(it);
        }
    }

    const SInt32 nTargetCommitted = static_cast<SInt32>(ComputeCommittedCount(next_committed_percentage, unNumKilobots));
    const SInt32 nDeltaCommitted = nTargetCommitted - unInitialCommitted;
    const bool bAbruptVariation = (end_commitment_variation_time == 0 || end_commitment_variation_time <= start_commitment_variation_time);

    std::vector<UInt16> vecCandidates = (nDeltaCommitted >= 0) ? vecUncommitted : vecCommitted;
    for(UInt16 it = vecCandidates.size(); it > 1; --it){
        std::swap(vecCandidates[it - 1], vecCandidates[rand() % it]);
    }

    std::vector<UInt8> vecNeedsOdd(unNumKilobots, 0);
    UInt16 unOddCount = static_cast<UInt16>(std::abs(nDeltaCommitted));
    if(unOddCount > vecCandidates.size()) unOddCount = vecCandidates.size();
    for(UInt16 it = 0; it < unOddCount; ++it){
        vecNeedsOdd[vecCandidates[it]] = 1;
    }

    for(UInt16 it = 0; it < unNumKilobots; ++it){
        UInt8 unNumFlips = 0;
        if(vecNeedsOdd[it]){
            unNumFlips = bAbruptVariation ? 1 : static_cast<UInt8>(2 * (rand() % 5) + 1);
        }
        else{
            unNumFlips = bAbruptVariation ? 0 : static_cast<UInt8>(2 * (rand() % 5));
        }
        m_vecVariationNumFlips[it] = unNumFlips;
        /*
         * Keep seed in [0x0800, 0x09FF]:
         * - receiver can reject corrupted payloads;
         * - upper nibble of seed payload cannot overlap start/end tags.
         */
        m_vecVariationSeeds[it] = static_cast<UInt16>(0x0800 | (rand() & 0x01FF));
    }
}

/****************************************/
/****************************************/

void CBestN_ALF::SetupVirtualEnvironments(TConfigurationNode& t_tree){
    CSimulator &simulator = GetSimulator();
    m_random_seed = simulator.GetRandomSeed();
    /* Get the structure variables from the .argos file*/
    TConfigurationNode& tHierarchicalStructNode=GetNode(t_tree,"hierarchicStruct");
    GetNodeAttribute(tHierarchicalStructNode,"rebroadcast",rebroadcast);
    GetNodeAttribute(tHierarchicalStructNode,"committed_percentage",committed_percentage);
    GetNodeAttribute(tHierarchicalStructNode,"queue_lenght",queue_lenght);
    GetNodeAttribute(tHierarchicalStructNode,"msg_expiring_seconds",expiring_quorum_seconds);
    GetNodeAttribute(tHierarchicalStructNode,"start_commitment_variation_time",start_commitment_variation_time);
    GetNodeAttribute(tHierarchicalStructNode,"end_commitment_variation_time",end_commitment_variation_time);
    GetNodeAttribute(tHierarchicalStructNode,"next_committed_percentage",next_committed_percentage);
    GetNodeAttribute(tHierarchicalStructNode,"quorum_threshold",quorum_threshold);
    if(start_commitment_variation_time==0) variation_done = true;
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
                    SendStateInformation(c_kilobot_entity);
                    break;
                case 2:
                    m_vecStart_experiment[unKilobotID]=3;
                    SendVariationStartInformation(c_kilobot_entity);
                    break;
                case 3:
                    m_vecStart_experiment[unKilobotID]=4;
                    SendVariationEndInformation(c_kilobot_entity);
                    break;
                case 4:
                    m_vecStart_experiment[unKilobotID]=5;
                    SendVariationSeedInformation(c_kilobot_entity);
                    break;
                case 5:
                    m_vecStart_experiment[unKilobotID]=6;
                    SendInformationGPS(c_kilobot_entity);
                    break;
            }
            start_experiment=1;
            for(UInt16 i=0;i<m_vecStart_experiment.size();i++){
                if(m_vecStart_experiment[i]!=6){
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
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 0;
    tKilobotMessage.m_sType = rebroadcast;
    tKilobotMessage.m_sID = expiring_quorum_seconds;
    tKilobotMessage.m_sData = queue_lenght;
    // Fill the kilobot message by the ARK-type messages
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = (UInt8)(tMessage.m_sID >> 7) << 1;
        m_tMessages[unKilobotID].data[1+i*3] = tMessage.m_sID << 1 | tMessage.m_sData >> 6;
        m_tMessages[unKilobotID].data[2+i*3] = tMessage.m_sData << 2 | tMessage.m_sType;
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendInformationGPS(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 1;
    tKilobotMessage.m_sType = 0;
    UInt8 angle = (UInt8)((m_vecKilobotOrientations[unKilobotID].GetValue()) * 0.0417);
    UInt8 valX = (UInt8)((m_vecKilobotPositions[unKilobotID].GetX() + this->GetSpace().GetArenaLimits().GetMax()[0]) * 100)*.5;
    UInt8 valY = (UInt8)((m_vecKilobotPositions[unKilobotID].GetY() + this->GetSpace().GetArenaLimits().GetMax()[1]) * 100)*.5;   
    tKilobotMessage.m_sType = (valY & 0b00000111) << 1 | tKilobotMessage.m_sType;
    tKilobotMessage.m_sID = unKilobotID << 3 | angle >> 1;
    tKilobotMessage.m_sData = valX << 4 | (valY >> 3) << 1 | (angle & 0b00000001);
    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = (tKilobotMessage.m_sID >> 3) << 1;
        m_tMessages[unKilobotID].data[1+i*3] = (tKilobotMessage.m_sData >> 4) <<2 | (tKilobotMessage.m_sID & 0b0000000110) >> 1;
        m_tMessages[unKilobotID].data[2+i*3] = (tKilobotMessage.m_sID & 0b0000000001) << 7 | (tKilobotMessage.m_sData & 0b0000000001) << 6 | (tKilobotMessage.m_sData & 0b0000001110) << 2 | ((tKilobotMessage.m_sType & 0b1110) >> 1);
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendStateInformation(CKilobotEntity &c_kilobot_entity){
    /* Get the kilobot ID */
    UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    m_vecLastTimeMessaged[unKilobotID]=m_fTimeInSeconds;
    /* Create ARK-type messages variables */
    m_tALFKilobotMessage tKilobotMessage,tEmptyMessage,tMessage;
    m_tMessages[unKilobotID].type = 0;
    tKilobotMessage.m_sType = 1;
    tKilobotMessage.m_sID = unKilobotID;
    tKilobotMessage.m_sID           = quorum_threshold*100;
    tKilobotMessage.m_sID           = tKilobotMessage.m_sID << 7 | unKilobotID;
    tKilobotMessage.m_sData         = quorum_threshold*100;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData >> 3;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData << 5 ;
    tKilobotMessage.m_sData         = tKilobotMessage.m_sData << 1 | m_vecKilobotStates[unKilobotID];    // Prepare an empty ARK-type message to fill the gap in the full kilobot message
    tEmptyMessage.m_sID = 1023;
    tEmptyMessage.m_sType = 0;
    tEmptyMessage.m_sData = 0;
    // Fill the kilobot message by the ARK-type messages
    for (UInt8 i = 0; i < 3; ++i){
        if( i == 0){
            tMessage = tKilobotMessage;
        }
        else{
            tMessage = tEmptyMessage;
        }
        m_tMessages[unKilobotID].data[i*3] = tKilobotMessage.m_sID << 1 | tKilobotMessage.m_sType;
        m_tMessages[unKilobotID].data[1+i*3] = (tKilobotMessage.m_sData >> 6) << 3 | (tKilobotMessage.m_sID >> 7)  ;
        m_tMessages[unKilobotID].data[2+i*3] = tKilobotMessage.m_sData & 0b0000111111;
    }
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendVariationStartInformation(CKilobotEntity &c_kilobot_entity){
    const UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    const UInt16 unPayload = static_cast<UInt16>(VARIATION_START_TAG | (start_commitment_variation_time & VARIATION_TIME_MASK));
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;
    PrepareSimpleIndividualMSG(m_tMessages[unKilobotID], unKilobotID, unPayload);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendVariationEndInformation(CKilobotEntity &c_kilobot_entity){
    const UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    const UInt16 unPayload = static_cast<UInt16>(VARIATION_END_TAG | (end_commitment_variation_time & VARIATION_TIME_MASK));
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;
    PrepareSimpleIndividualMSG(m_tMessages[unKilobotID], unKilobotID, unPayload);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
}

/****************************************/
/****************************************/

void CBestN_ALF::SendVariationSeedInformation(CKilobotEntity &c_kilobot_entity){
    const UInt16 unKilobotID = GetKilobotId(c_kilobot_entity);
    const UInt16 unPayload = static_cast<UInt16>((m_vecVariationSeeds[unKilobotID] << 4) | (m_vecVariationNumFlips[unKilobotID] & 0x0F));
    m_vecLastTimeMessaged[unKilobotID] = m_fTimeInSeconds;
    PrepareSimpleIndividualMSG(m_tMessages[unKilobotID], unKilobotID, unPayload);
    GetSimulator().GetMedium<CKilobotCommunicationMedium>("kilocomm").SendOHCMessageTo(c_kilobot_entity,&m_tMessages[unKilobotID]);
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
    if(abs(vec_position_on_plane.GetX())>this->GetSpace().GetArenaLimits().GetMax()[0]-0.05 || abs(vec_position_on_plane.GetY())>this->GetSpace().GetArenaLimits().GetMax()[1]-0.05) color=CColor::BLACK;
    return color;
}

REGISTER_LOOP_FUNCTIONS(CBestN_ALF, "ALF_BestN_loop_function")
