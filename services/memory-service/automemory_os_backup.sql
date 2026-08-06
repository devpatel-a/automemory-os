--
-- PostgreSQL database dump
--

\restrict w0nX0xV55gc9KFjp6O3STWEzxdQfjuCnmmuHHHvdSrpb5W6oNTI4K6Txi8Vt7Jl

-- Dumped from database version 14.20 (Homebrew)
-- Dumped by pg_dump version 14.20 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: memories; Type: TABLE; Schema: public; Owner: devpatel
--

CREATE TABLE public.memories (
    id integer NOT NULL,
    content text NOT NULL,
    category character varying(50) NOT NULL,
    importance double precision NOT NULL,
    access_count integer NOT NULL,
    state character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_accessed timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.memories OWNER TO devpatel;

--
-- Name: memories_id_seq; Type: SEQUENCE; Schema: public; Owner: devpatel
--

CREATE SEQUENCE public.memories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.memories_id_seq OWNER TO devpatel;

--
-- Name: memories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: devpatel
--

ALTER SEQUENCE public.memories_id_seq OWNED BY public.memories.id;


--
-- Name: memories id; Type: DEFAULT; Schema: public; Owner: devpatel
--

ALTER TABLE ONLY public.memories ALTER COLUMN id SET DEFAULT nextval('public.memories_id_seq'::regclass);


--
-- Data for Name: memories; Type: TABLE DATA; Schema: public; Owner: devpatel
--

COPY public.memories (id, content, category, importance, access_count, state, created_at, last_accessed) FROM stdin;
1	Driver likes coffee	preference	0.9500000000000002	15	active	2026-07-29 09:38:02.101917+05:30	2026-08-02 21:07:17.630269+05:30
2	My name is Dev Patel	profile	0.95	3	active	2026-07-30 19:47:34.23457+05:30	2026-08-02 21:07:17.630282+05:30
3	I prefer dark mode	preference	0.8	3	active	2026-07-30 19:47:52.794816+05:30	2026-08-02 21:07:17.630286+05:30
4	I study Python every evening	habit	0.7	3	active	2026-07-30 19:48:08.42894+05:30	2026-08-02 21:07:17.630289+05:30
\.


--
-- Name: memories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: devpatel
--

SELECT pg_catalog.setval('public.memories_id_seq', 4, true);


--
-- Name: memories memories_pkey; Type: CONSTRAINT; Schema: public; Owner: devpatel
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict w0nX0xV55gc9KFjp6O3STWEzxdQfjuCnmmuHHHvdSrpb5W6oNTI4K6Txi8Vt7Jl

