from models.member_layer import Application


def qualifies(application: Application) -> bool:
    if not application.email:
        return False
    if application.program_key != "homeowner_protection":
        return False
    if not application.answers_json:
        return False
    return True
