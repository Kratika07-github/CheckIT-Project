# supabase_client.py
from supabase import create_client
from django.conf import settings

def get_supabase():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
