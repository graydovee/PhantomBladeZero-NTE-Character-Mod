"""Define source-to-native humanoid roles and helper folding tables."""

MAIN = {
    # game bone            -> zero bone
    "root": "Bip001",
    "pelvis": "Bip001-Pelvis",
    "spine_01": "Bip001-Spine",
    "spine_02": "Bip001-Spine1",
    "spine_03": "Bip001-Spine2",
    "neck_01": "Bip001-Neck",
    "neck_02": "Bip001-Neck1",
    "head": "Bip001-Head",
}
for s, S in (("l", "L"), ("r", "R")):
    MAIN.update({
        "clavicle_%s" % s: "Bip001-%s-Clavicle" % S,
        "upperarm_%s" % s: "Bip001-%s-UpperArm" % S,
        "lowerarm_%s" % s: "Bip001-%s-Forearm" % S,
        "hand_%s" % s: "Bip001-%s-Hand" % S,
        "thigh_%s" % s: "Bip001-%s-Thigh" % S,
        "calf_%s" % s: "Bip001-%s-Calf" % S,
        "foot_%s" % s: "Bip001-%s-Foot" % S,
        "ball_%s" % s: "Bip001-%s-Toe0" % S,
    })
    # fingers: game <finger>_0X_s  <-  zero Finger<k>/Finger<k>1/Finger<k>2
    for game_f, k in (("index", 1), ("middle", 2), ("ring", 3), ("pinky", 4)):
        MAIN["%s_metacarpal_%s" % (game_f, s)] = "Bip001-%s-Finger%d" % (S, k)
        MAIN["%s_01_%s" % (game_f, s)] = "Bip001-%s-Finger%d" % (S, k)
        MAIN["%s_02_%s" % (game_f, s)] = "Bip001-%s-Finger%d1" % (S, k)
        MAIN["%s_03_%s" % (game_f, s)] = "Bip001-%s-Finger%d2" % (S, k)
    MAIN["thumb_01_%s" % s] = "Bip001-%s-Finger0" % S
    MAIN["thumb_02_%s" % s] = "Bip001-%s-Finger01" % S
    MAIN["thumb_03_%s" % s] = "Bip001-%s-Finger02" % S

FOLD = {
    "weapon_l": "hand_l", "weapon_l_child": "hand_l", "weapon_l_Inst": "hand_l",
    "weapon_r": "hand_r", "weapon_r_child": "hand_r", "weapon_r_Inst": "hand_r",
    "PT_weaponHandR": "hand_r", "PT_weaponHandL": "hand_l",
    "wrist_inner_l": "hand_l", "wrist_outer_l": "hand_l",
    "wrist_inner_r": "hand_r", "wrist_outer_r": "hand_r",
    "lowerarm_twist_01_l": "lowerarm_l", "lowerarm_twist_02_l": "lowerarm_l",
    "lowerarm_twist_01_r": "lowerarm_r", "lowerarm_twist_02_r": "lowerarm_r",
    "upperarm_twist_01_l": "upperarm_l", "upperarm_twist_02_l": "upperarm_l",
    "upperarm_twist_01_r": "upperarm_r", "upperarm_twist_02_r": "upperarm_r",
    "thigh_twist_01_l": "thigh_l", "thigh_twist_02_l": "thigh_l",
    "thigh_twist_01_r": "thigh_r", "thigh_twist_02_r": "thigh_r",
    "calf_twist_01_l": "calf_l", "calf_twist_02_l": "calf_l",
    "calf_twist_01_r": "calf_r", "calf_twist_02_r": "calf_r",
    "spine_04": "spine_03", "spine_05": "spine_03",
}

