from questionary import Style

custom_style = Style([
    ('qmark', 'fg:#ff9d00 bold'),        # Question mark
    ('question', 'bold'),                 # Question text
    ('answer', 'fg:#5F819D bold'),         # Submitted answer
    ('pointer', 'fg:#ff9d00 bold'),        # Pointer in selection list
    ('highlighted', 'fg:#ff9d00 bold'),
    ('selected', 'fg:#5F819D bold'),
    ('separator', 'fg:#cc5454'),
    ('instruction', 'fg:#8f9d9f italic'),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])

