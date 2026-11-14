-- Remove only the Mission 31 read-only command-center API.
drop function if exists public.papi_command_center_snapshot(integer);
