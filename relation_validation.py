import data
import util

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
    Otherwise => Return validaty False, filled reason string

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


def validate_S_parents(parents):
    """
    Validates the parents of a single sensor.

    Parameters:
        parents: list of relations.

    Returns:
        2-tuple of results (value and reason).
    """
    parents_HY = [
        c
        for c in parents
        if c["part_parent"]["kind_of_part"]["kind_of_part_id"]
        == data.KoPID_from_partKoPName["Hybrid"]
    ]

    return validate_S_par_HY(parents_HY)


def validate_sensor(S_part_id):
    """
    Validate a single sensor, given its part_id.
    """
    parents = util.get_parents(S_part_id)[0]
    validation_result_S_par_HY, validation_reason_S_par_HY = validate_S_parents(parents)
    validation_result = {
        "validation_result_S_par_HY": validation_result_S_par_HY,
        "validation_reason_S_par_HY": validation_reason_S_par_HY,
        "validation_result_overall": validation_result_S_par_HY,
    }
    return validation_result
