import hgtd_tools.data as data
import hgtd_tools.util as util

# =============================================================================
# This file contains validation functions to make sure relations are in order
# =============================================================================
# Idea:
## Capture the most common mistakes and report their occurences (+ why wrong)
# Structure:
## A: Go by parent => down to children
### 1. individual kinds of relations, if there are multiple for some parent KoP
### 2. combination of all relations to be validated for some parent KoP
### The existance of the parent implies all relations to children must be valid
## B: Go by child => up to parents
### 1. individual kinds of relations, if there are multiple for some child KoP
### 2. combination of all relations to be validated for some child KoP
### The existance of child does not require relation to parent (yet), new part
# How to use
## These functions can be called standalone, or as part of reporting wrapper
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# A - Parent: Module
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


def validate_DU_chi_MO(children_MO):
    """
    Check if a DU has exactly one MO at each position. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        children_MO: list of relations.

    """
    if len(children_MO) == 0:
        return (
            False,
            "Not a single Module connected, making no attempt at deciphering the DU type and expected slots.",
        )
    DU_SN = str(children_MO[0]["part_parent"]["serial_number"])
    actual_Number_of_connected_Modules = len(children_MO)
    for key in data.allDUs.keys():
        if key in DU_SN:
            DU_Type = key
            break
    else:
        return (
            False,
            "DU type could not be retrieved from serial number. Now stopping attempt at validating this DU.",
        )
    expected_DU_Slots = data.allDUs[DU_Type]
    # For the future: interlock_Slots = data.DU_Interlock_dict[DU_Type]
    expected_Number_of_connected_Modules = len(expected_DU_Slots)

    if actual_Number_of_connected_Modules < expected_Number_of_connected_Modules:
        return (
            False,
            f"Too few Modules connected ({actual_Number_of_connected_Modules}). Must be exactly {expected_Number_of_connected_Modules}, each at unique local position within DU.",
        )
    elif actual_Number_of_connected_Modules == expected_Number_of_connected_Modules:
        actual_filled_positions = list(rel["position"] for rel in children_MO)
        non_filled_but_expected_positions = []
        non_uniquely_filled_positions = {}
        for expected_slot in expected_DU_Slots:
            expected_position_to_validate = expected_slot["slot"]
            if expected_position_to_validate not in actual_filled_positions:
                non_filled_but_expected_positions.append(expected_position_to_validate)
            else:
                indices_where_actual_matches_this_expected_slot = [
                    index
                    for index, value in enumerate(actual_filled_positions)
                    if value == expected_position_to_validate
                ]
                if len(indices_where_actual_matches_this_expected_slot) > 1:
                    modules_occupying_same_expected_slot = []
                    for i in indices_where_actual_matches_this_expected_slot:
                        modules_occupying_same_expected_slot.append(
                            children_MO[i]["part"]["serial_number"]
                        )
                    non_uniquely_filled_positions[expected_slot] = (
                        modules_occupying_same_expected_slot
                    )
        non_uniquely_connected_modules = []
        for actual_child_MO in children_MO:
            if (
                len(
                    util.get_parents(
                        int(actual_child_MO["part"]["part_id"]), ofKind="Detector Unit"
                    )[0]
                )
                > 1
            ):
                non_uniquely_connected_modules.append(
                    actual_child_MO["part"]["serial_number"]
                )
        # Build the combined reason_string:
        reason_string = ""
        if non_filled_but_expected_positions != []:
            reason_string += (
                f"There are expected positions to which no Module connects to.\n"
            )
            reason_string += ", ".join(non_filled_but_expected_positions) + "\n"
        if non_uniquely_filled_positions != {}:
            reason_string += f"There are expected positions to which more than one Module connects to.\n"
            for key, value in non_uniquely_filled_positions.items():
                reason_string += f"{key}: " + ", ".join(value) + "\n"
        if non_uniquely_connected_modules != []:
            reason_string += f"There are modules connected to this DU under investigation which have more than one relation to a DU parent.\n"
            reason_string += ", ".join(non_uniquely_connected_modules) + "\n"
        if reason_string != "":
            return False, reason_string
        else:
            return True, ""
    else:
        return (
            False,
            f"Too many Modules connected ({actual_Number_of_connected_Modules}). Must be exactly {expected_Number_of_connected_Modules}, each at unique local position within DU.",
        )


def validate_DU_chi_SU(children_SU):
    """
    Check if a DU has exactly one SU at empty position. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        children_SU: list of relations.

    """
    if len(children_SU) == 0:
        return (
            False,
            "No Support Unit connected, must be exactly one at empty position.",
        )
    elif len(children_SU) == 1:
        if str(children_SU[0]["position"]) != "":
            return (
                False,
                f"Exactly one SU connected, but at wrong position {str(children_SU[0]["position"])}, where it should have been empty position.",
            )
        DU_SN = str(children_SU[0]["part_parent"]["serial_number"])
        for key in data.allDUs.keys():
            if key in DU_SN:
                DU_Type = key
                break
        else:
            return (
                False,
                "DU type could not be retrieved from serial number. Now stopping attempt at validating this DU.",
            )
        SU_SN = str(children_SU[0]["part"]["serial_number"])
        for key in data.allDUs.keys():
            if key in SU_SN:
                SU_Type = key
                break
        else:
            return (
                False,
                "SU type of the single SU connected to this DU could not be retrieved from serial number. Now stopping attempt at validating this DU.",
            )
        if SU_Type != DU_Type:
            return (
                False,
                f"Type of DU ({DU_Type}) and Type of SU ({SU_Type}) as inferred from their serial numbers ({DU_SN} and {SU_SN}, respectively) do not match.",
            )
        else:
            return True, ""
    else:
        return (
            False,
            f"Too many ({len(children_SU)}) Support Units connected, must be exactly one at empty position.",
        )


def validate_DU_children(children):
    """
    Validates the children of a single detector unit.

    Parameters:
        children: list of relations.

    Returns:
        2-tuple of results for both checks (MO, SU).
    """
    children_MO = [
        c
        for c in children
        if c["part"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Module"]
    ]
    children_SU = [
        c
        for c in children
        if c["part"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Support Unit"]
    ]

    return validate_DU_chi_MO(children_MO), validate_DU_chi_SU(children_SU)


def validate_DU(DU_part_id):
    """
    Validate a single detector unit, given its part_id.
    """
    children = util.get_children(DU_part_id)[0]
    (validation_result_DU_chi_MO, validation_reason_DU_chi_MO), (
        validation_result_DU_chi_SU,
        validation_reason_DU_chi_SU,
    ) = validate_DU_children(children)
    validation_result = {
        "validation_result_DU_chi_MO": validation_result_DU_chi_MO,
        "validation_reason_DU_chi_MO": validation_reason_DU_chi_MO,
        "validation_result_DU_chi_SU": validation_result_DU_chi_SU,
        "validation_reason_DU_chi_SU": validation_reason_DU_chi_SU,
        "validation_result_overall": validation_result_DU_chi_MO
        and validation_result_DU_chi_SU,
    }
    return validation_result


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# A - Parent: Module
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


def validate_MO_chi_MF(children_MF):
    """
    Check if a module has exactly one module flex child, with empty position. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        children_MF: list of relations.

    Counting the correct number of children always takes precedence (no further checks for position in that case).
    """
    if len(children_MF) == 0:
        return (
            False,
            "No Module Flex connected. Must be exactly one, at empty position.",
        )
    elif len(children_MF) == 1:
        position_attribute = str(children_MF[0]["position"])
        SN_MF = str(children_MF[0]["part"]["serial_number"])
        if position_attribute != "":
            return (
                False,
                f"One Module Flex {SN_MF} connected, but wrong position attribute {position_attribute}.",
            )
        else:
            return True, ""
    else:
        return (
            False,
            "Multiple Module Flex children connected. Must be exactly one, at empty position.",
        )


def validate_MO_chi_HY(children_HY):
    """
    Check if a module has exactly one hybrid at position HV, exactly one hybrid at position LV. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        children_HY: list of relations.

    Counting the correct number of children always takes precedence (no further checks for position in that case).
    """
    if len(children_HY) == 0:
        return (
            False,
            "No Hybrid connected. Must be exactly two, one at position HV, and one at position LV.",
        )
    elif len(children_HY) == 1:
        return (
            False,
            "Only one Hybrid connected. Must be exactly two, one at position HV, and one at position LV.",
        )
    elif len(children_HY) == 2:
        position_attribute_0 = str(children_HY[0]["position"])
        SN_HY_0 = str(children_HY[0]["part"]["serial_number"])
        position_attribute_1 = str(children_HY[1]["position"])
        SN_HY_1 = str(children_HY[1]["part"]["serial_number"])

        if position_attribute_0 == "HV":
            if position_attribute_1 == "LV":
                return True, ""
            elif position_attribute_1 == "HV":
                return (
                    False,
                    "Two Hybrids connected, but both at HV position. Must be exactly two, one at position HV, and one at position LV.",
                )
            else:
                return (
                    False,
                    f"Two Hybrids connected, but Hybrid {SN_HY_1} at wrong position {position_attribute_1}. Must be exactly two, one at position HV, and one at position LV.",
                )
        elif position_attribute_0 == "LV":
            if position_attribute_1 == "HV":
                return True, ""
            elif position_attribute_1 == "LV":
                return (
                    False,
                    "Two Hybrids connected, but both at LV position. Must be exactly two, one at position HV, and one at position LV.",
                )
            else:
                return (
                    False,
                    f"Two Hybrids connected, but Hybrid {SN_HY_1} at wrong position {position_attribute_1}. Must be exactly two, one at position HV, and one at position LV.",
                )
        else:
            # at least child 0 has a wrong position attribute! Test also for child 1:
            if position_attribute_1 not in ["HV", "LV"]:
                # child 1 is also not ok
                return (
                    False,
                    "Two Hybrids connected, but none of them at the position HV or LV. Must be exactly two, one at position HV, and one at position LV.",
                )
            else:
                # child 1 is ok, but child 0 is not
                return (
                    False,
                    f"Two Hybrids connected, but Hybrid {SN_HY_0} at wrong position {position_attribute_0}. Must be exactly two, one at position HV, and one at position LV.",
                )
    else:
        return (
            False,
            "More than two Hybrid children connected. Must be exactly two, one at position HV, and one at position LV.",
        )


def validate_MO_children(children):
    """
    Validates the children of a single module.

    Parameters:
        children: list of relations.

    Returns:
        2-tuple of results for both checks (MF, HY).
    """
    children_MF = [
        c
        for c in children
        if c["part"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Module Flex"]
    ]
    children_HY = [
        c
        for c in children
        if c["part"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Hybrid"]
    ]

    return validate_MO_chi_MF(children_MF), validate_MO_chi_HY(children_HY)


def validate_module(MO_part_id):
    """
    Validate a single module, given its part_id.
    """
    children = util.get_children(MO_part_id)[0]
    (validation_result_MO_chi_MF, validation_reason_MO_chi_MF), (
        validation_result_MO_chi_HY,
        validation_reason_MO_chi_HY,
    ) = validate_MO_children(children)
    validation_result = {
        "validation_result_MO_chi_MF": validation_result_MO_chi_MF,
        "validation_reason_MO_chi_MF": validation_reason_MO_chi_MF,
        "validation_result_MO_chi_HY": validation_result_MO_chi_HY,
        "validation_reason_MO_chi_HY": validation_reason_MO_chi_HY,
        "validation_result_overall": validation_result_MO_chi_MF
        and validation_result_MO_chi_HY,
    }
    return validation_result


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# A - Parent: Hybrid
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


def validate_HY_chi_S(children_S):
    """
    Check if a hybrid has exactly one sensor child, with empty position. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        children_S: list of relations.

    Counting the correct number of children always takes precedence (no further checks for position in that case).
    """
    if len(children_S) == 0:
        return (
            False,
            "No Sensor connected. Must be exactly one, at empty position.",
        )
    elif len(children_S) == 1:
        position_attribute = str(children_S[0]["position"])
        SN_S = str(children_S[0]["part"]["serial_number"])
        if position_attribute != "":
            return (
                False,
                f"One Sensor {SN_S} connected, but wrong position attribute {position_attribute}.",
            )
        else:
            return True, ""
    else:
        return (
            False,
            "Multiple Sensor children connected. Must be exactly one, at empty position.",
        )


def validate_HY_children(children):
    """
    Validates the children of a single hybrid.

    Parameters:
        children: list of relations.

    Returns:
        2-tuple of results (value and reason).
    """
    children_S = [
        c
        for c in children
        if c["part"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Sensor"]
    ]

    return validate_HY_chi_S(children_S)


def validate_hybrid(HY_part_id):
    """
    Validate a single hybrid, given its part_id.
    """
    children = util.get_children(HY_part_id)[0]
    validation_result_HY_chi_S, validation_reason_HY_chi_S = validate_HY_children(
        children
    )
    validation_result = {
        "validation_result_HY_chi_S": validation_result_HY_chi_S,
        "validation_reason_HY_chi_S": validation_reason_HY_chi_S,
        "validation_result_overall": validation_result_HY_chi_S,
    }
    return validation_result


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# B - Child: Sensor
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


def validate_S_par_HY(parents_HY):
    """
    Check if a sensor has exactly one hybrid parent, with empty position. => Return validity True, empty reason string
    No parent connected yet => Return validity "new"
    Otherwise => Return validity False, filled reason string

    Parameters:
        parents_HY: list of relations.

    Counting the correct number of parents always takes precedence (no further checks for position in that case).
    """
    if len(parents_HY) == 0:
        return (
            "new",
            "No Hybrid connected. This is acceptable during production process, sensor has not been used yet.",
        )
    elif len(parents_HY) == 1:
        position_attribute = str(parents_HY[0]["position"])
        SN_HY = str(parents_HY[0]["part_parent"]["serial_number"])
        if position_attribute != "":
            return (
                False,
                f"One Hybrid {SN_HY} connected, but wrong position attribute {position_attribute}.",
            )
        else:
            return True, ""
    else:
        return (
            False,
            "Multiple Hybrid parents connected. Must be exactly one, at empty position.",
        )


def validate_S_par_W(parents_W):
    """
    Check if a sensor has exactly one wafer parent, with filled empty position or position matching its SN. => Return validity True, empty reason string
    Otherwise => Return validity False, filled reason string

    Parameters:
        parents_W: list of relations.

    Counting the correct number of parents always takes precedence (no further checks for position in that case).
    """
    if len(parents_W) == 0:
        return (
            False,
            "No Wafer parent connected. Must be exactly one, at position in Wafer matching exactly last two digits of child Sensor SN.",
        )
    elif len(parents_W) == 1:
        position_attribute = str(parents_W[0]["position"])
        SN_W = str(parents_W[0]["part_parent"]["serial_number"])
        SN_S = str(parents_W[0]["part"]["serial_number"])
        if position_attribute != "" and position_attribute != SN_S[-2:]:
            return (
                False,
                f"One Wafer {SN_W} connected, but wrong position attribute {position_attribute}. Position in Wafer must be either empty (in that case, position is stored in Sensor attributes) or filled, to match exactly last two digits of child Sensor SN.",
            )
        else:
            return True, ""
    else:
        return (
            False,
            "Multiple Wafer parents connected. Must be exactly one, at position in Wafer matching exactly last two digits of child Sensor SN.",
        )


def validate_S_parents(parents):
    """
    Validates the parents of a single sensor.

    Parameters:
        parents: list of relations.

    Returns:
        2-tuple of results for both checks (HY, W).
    """
    parents_HY = [
        c
        for c in parents
        if c["part_parent"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Hybrid"]
    ]
    parents_W = [
        c
        for c in parents
        if c["part_parent"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Wafer"]
    ]

    return validate_S_par_HY(parents_HY), validate_S_par_W(parents_W)


def validate_sensor(S_part_id):
    """
    Validate a single sensor, given its part_id.
    """
    parents = util.get_parents(S_part_id)[0]
    (validation_result_S_par_HY, validation_reason_S_par_HY), (
        validation_result_S_par_W,
        validation_reason_S_par_W,
    ) = validate_S_parents(parents)
    if validation_result_S_par_HY != "new":
        # if it's not new, then use the same boolean result for overall
        validation_result_S_par_HY_for_overall = validation_result_S_par_HY
    else:
        # for overall result, S_par_HY being new evaluates to False
        validation_result_S_par_HY_for_overall = False
    validation_result = {
        "validation_result_S_par_HY": validation_result_S_par_HY,
        "validation_reason_S_par_HY": validation_reason_S_par_HY,
        "validation_result_S_par_W": validation_result_S_par_W,
        "validation_reason_S_par_W": validation_reason_S_par_W,
        "validation_result_overall": validation_result_S_par_HY_for_overall
        and validation_result_S_par_W,
    }
    return validation_result
