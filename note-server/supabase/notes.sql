-- Note metadata and vectors. Plaintext note content is never stored here.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.buddy_note_chunks (
    owner_id text NOT NULL,
    chunk_id uuid NOT NULL,
    relative_path text NOT NULL,
    heading text,
    chunk_number integer NOT NULL CHECK (chunk_number >= 0),
    content_hash text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS public.buddy_note_embeddings (
    owner_id text NOT NULL,
    chunk_id uuid NOT NULL,
    content_hash text NOT NULL,
    embedding extensions.vector(768) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, chunk_id)
);

ALTER TABLE public.buddy_note_embeddings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.buddy_note_embeddings FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
ON public.buddy_note_embeddings TO service_role;

ALTER TABLE public.buddy_note_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.buddy_note_chunks FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
ON public.buddy_note_chunks TO service_role;

CREATE INDEX IF NOT EXISTS buddy_note_embeddings_cosine_idx
ON public.buddy_note_embeddings
USING hnsw (embedding extensions.vector_cosine_ops);

CREATE OR REPLACE FUNCTION public.match_buddy_note_embeddings(
    match_owner_id text,
    query_embedding extensions.vector(768),
    match_count integer DEFAULT 10,
    match_threshold double precision DEFAULT 0.25
)
RETURNS TABLE (chunk_id uuid, similarity double precision)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT item.chunk_id,
           1 - (
               item.embedding OPERATOR(extensions.<=>) query_embedding
           ) AS similarity
    FROM public.buddy_note_embeddings AS item
    WHERE item.owner_id = match_owner_id
      AND 1 - (
          item.embedding OPERATOR(extensions.<=>) query_embedding
      ) >= match_threshold
    ORDER BY item.embedding OPERATOR(extensions.<=>) query_embedding
    LIMIT match_count;
$$;

REVOKE ALL ON FUNCTION public.match_buddy_note_embeddings(
    text, extensions.vector, integer, double precision
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_buddy_note_embeddings(
    text, extensions.vector, integer, double precision
) TO service_role;
