def is_authenticated(user):  # pragma: no cover
    if callable(user.is_authenticated):
        return user.is_authenticated()
    else:
        return user.is_authenticated
