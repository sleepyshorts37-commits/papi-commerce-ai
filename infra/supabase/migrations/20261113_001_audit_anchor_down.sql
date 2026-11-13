-- Rollback 20261113_001: remove the external audit checkpoint anchor.
-- Deliberately refuses rollback when audit evidence exists; export/retain it first.
BEGIN;

DO $rollback$
BEGIN
    IF EXISTS (SELECT 1 FROM public.papi_audit_anchor_records)
       OR EXISTS (SELECT 1 FROM public.papi_audit_anchor_heads) THEN
        RAISE EXCEPTION 'Rollback refused: audit anchor records or heads exist; preserve/export evidence before removal'
            USING ERRCODE = '55000';
    END IF;
END;
$rollback$;

DROP FUNCTION IF EXISTS public.papi_advance_audit_anchor(text, text, text);
DROP TRIGGER IF EXISTS papi_audit_anchor_records_immutable ON public.papi_audit_anchor_records;
DROP FUNCTION IF EXISTS public.papi_reject_audit_anchor_record_mutation();
DROP TABLE IF EXISTS public.papi_audit_anchor_heads;
DROP TABLE IF EXISTS public.papi_audit_anchor_records;
-- pgcrypto and the shared extensions schema are intentionally retained:
-- other application features may depend on them.

COMMIT;
