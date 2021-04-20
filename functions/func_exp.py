def sort_roles(roles: list, exp: int) -> [dict, dict]:
    # filters the input roles and only returns the roles which the user has earned and which ones they will earn next
    roles_earned = [{"role": item["role"], "requirement": item["requirement"]} for item in roles
                    if item["requirement"] <= exp]
    roles_next = [{"role": item["role"], "requirement": item["requirement"]} for item in roles
                  if item["requirement"] > exp]
    return roles_earned, roles_next
