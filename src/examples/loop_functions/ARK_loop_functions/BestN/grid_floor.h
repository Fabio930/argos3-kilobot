/**
 * @file <grid_floor.h>
 *
 * @author Fabio Oddi <fabio.oddi@uniroma1.it>
 */

#ifndef GRIDFLOOR_H
#define GRIDFLOOR_H
#include <argos3/core/utility/datatypes/datatypes.h>

#include <algorithm>
#include <vector>

using namespace argos;
class CGridFloor {
public:
    UInt32 Rows = 0, Cols = 0;
    Real XMin = 0, YMin = 0;
    Real InvCellSizeX = 0, InvCellSizeY = 0;
    std::vector<UInt8> ColorId;             

    inline UInt32 Index(UInt32 r, UInt32 c) const { return r * Cols + c; }

    inline UInt8 GetColorIdAt(const CVector2& p) const {
        if(Rows == 0 || Cols == 0 || ColorId.empty()) {
            return 225;
        }
        SInt32 c = static_cast<SInt32>(std::floor((p.GetX() - XMin) * InvCellSizeX));
        SInt32 r = static_cast<SInt32>(std::floor((p.GetY() - YMin) * InvCellSizeY));
        c = std::max<SInt32>(0, std::min<SInt32>(c, static_cast<SInt32>(Cols) - 1));
        r = std::max<SInt32>(0, std::min<SInt32>(r, static_cast<SInt32>(Rows) - 1));
        return ColorId[Index(r, c)];
    }

    inline CColor GetColorAt(const CVector2& p) const {
        UInt8 unId = GetColorIdAt(p);
        if(unId < 255) {
            unId = static_cast<UInt8>(((unId - 1) % 6));
        }
        switch(unId) {
            case 0: return CColor::RED;     // best
            case 1: return CColor::GREEN;
            case 2: return CColor::BLUE;
            case 3: return CColor::YELLOW;
            case 4: return CColor::CYAN;
            case 5: return CColor::MAGENTA;
            default: return CColor::WHITE;
        }
    }
};

#endif
