-- Remove only the Mission 32 scoped memory reader.
drop function if exists public.papi_list_memory_events(text,timestamptz,uuid,integer);
