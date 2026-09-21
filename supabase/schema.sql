-- BAH v2 analytics schema
-- Run this entire file once in Supabase SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  session_id text not null,
  event_type text not null check (event_type in ('chat', 'feedback', 'error')),
  message_id text,
  course text,
  question_type text,
  language text,
  input_length integer check (input_length is null or input_length >= 0),
  output_length integer check (output_length is null or output_length >= 0),
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  model_version text,
  feedback text check (feedback in ('positive', 'negative') or feedback is null),
  feedback_reason text,
  store_content boolean not null default false,
  question_text text,
  answer_text text,
  user_agent text
);

create index if not exists usage_events_created_at_idx
  on public.usage_events(created_at desc);
create index if not exists usage_events_event_type_idx
  on public.usage_events(event_type);
create index if not exists usage_events_session_id_idx
  on public.usage_events(session_id);
create index if not exists usage_events_feedback_idx
  on public.usage_events(feedback);
create index if not exists usage_events_course_idx
  on public.usage_events(course);

alter table public.usage_events enable row level security;

-- Browser clients never access this table directly.
revoke all on table public.usage_events from anon, authenticated;
grant all on table public.usage_events to service_role;

create or replace function public.admin_overview()
returns json
language sql
security definer
set search_path = public
as $$
  select json_build_object(
    'requests', count(*) filter (where event_type = 'chat'),
    'unique_sessions', count(distinct session_id) filter (where event_type = 'chat'),
    'positive_feedback', count(*) filter (where event_type = 'feedback' and feedback = 'positive'),
    'negative_feedback', count(*) filter (where event_type = 'feedback' and feedback = 'negative'),
    'avg_latency_ms', coalesce(round(avg(latency_ms)::numeric, 2) filter (where event_type = 'chat'), 0)
  )
  from public.usage_events;
$$;

create or replace function public.admin_feedback_reasons()
returns table(reason text, count bigint, percentage numeric)
language sql
security definer
set search_path = public
as $$
  with totals as (
    select count(*)::numeric as n
    from public.usage_events
    where event_type = 'feedback' and feedback = 'negative'
  )
  select
    coalesce(e.feedback_reason, 'Unspecified') as reason,
    count(*) as count,
    round((count(*)::numeric / nullif(t.n, 0)) * 100, 1) as percentage
  from public.usage_events e
  cross join totals t
  where e.event_type = 'feedback' and e.feedback = 'negative'
  group by coalesce(e.feedback_reason, 'Unspecified'), t.n
  order by count desc;
$$;

create or replace function public.admin_course_breakdown()
returns table(course text, count bigint, percentage numeric)
language sql
security definer
set search_path = public
as $$
  with totals as (
    select count(*)::numeric as n
    from public.usage_events
    where event_type = 'chat'
  )
  select
    coalesce(e.course, 'Unspecified') as course,
    count(*) as count,
    round((count(*)::numeric / nullif(t.n, 0)) * 100, 1) as percentage
  from public.usage_events e
  cross join totals t
  where e.event_type = 'chat'
  group by coalesce(e.course, 'Unspecified'), t.n
  order by count desc;
$$;

create or replace function public.admin_daily_usage()
returns table(day date, chats bigint, sessions bigint, avg_latency_ms numeric)
language sql
security definer
set search_path = public
as $$
  select
    created_at::date as day,
    count(*) as chats,
    count(distinct session_id) as sessions,
    coalesce(round(avg(latency_ms)::numeric, 0), 0) as avg_latency_ms
  from public.usage_events
  where event_type = 'chat'
    and created_at >= now() - interval '14 days'
  group by created_at::date
  order by day desc;
$$;

revoke all on function public.admin_overview() from public;
revoke all on function public.admin_feedback_reasons() from public;
revoke all on function public.admin_course_breakdown() from public;
revoke all on function public.admin_daily_usage() from public;

grant execute on function public.admin_overview() to service_role;
grant execute on function public.admin_feedback_reasons() to service_role;
grant execute on function public.admin_course_breakdown() to service_role;
grant execute on function public.admin_daily_usage() to service_role;
