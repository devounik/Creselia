from fastapi.templating import Jinja2Templates

# Templates configuration
templates = Jinja2Templates(directory="app/templates")

def get_templates():
    """Dependency to get templates instance"""
    return templates 