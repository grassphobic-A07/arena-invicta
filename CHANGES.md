## Added
- `discussions/migrations/0002_discussionthread_news_alter_discussionthread_body.py` to link discussion threads to news entries.
- JSON endpoints (`discussions.views.thread_list_api`, `thread_create_api`) and URL routes for fetching and creating threads asynchronously.
- Responsive Tailwind-based templates (`discussions/thread_list.html`, `thread_preview_card.html`, revamped `thread_detail.html`, `thread_form.html`) with modal markup and toast-ready interaction hooks.
- Client-side script (inline within `thread_list.html`) supporting AJAX thread creation, live search, modal orchestration, and card rendering.
- API-focused tests in `discussions/tests.py` validating search filters and creation workflow.

## Modified
- `discussions/models.py` to add the `news` relationship and helper metadata accessors.
- `discussions/forms.py` to expose the news selector and Tailwind-friendly widgets.
- `discussions/views.py` to support enriched context payloads, JSON responses, and annotated thread/comment data.
- `discussions/templates/discussions/thread_detail.html` and supporting templates for news linkage, author metadata, and modern layout.
- `discussions/admin.py` listings to surface associated news and improved filters.
- Navigation highlight (previous change) now aligns with `thread-list`.

## Fixed
- Ensured active-state comparisons and template renders safely handle missing author profiles and avoid duplicated fallback logic.
- Resolved missing toast feedback and stale state in the discussions list by unifying fetch/render logic and clearing validation errors on modal reuse.

## Notes
- The `news` field on `DiscussionThread` remains nullable for backward compatibility; future data cleanup can enforce non-null once legacy records are mapped.
- The AJAX endpoints are `csrf_exempt` to mirror the existing news module; consider adding token handling before production hardening.
- Run `python manage.py migrate` to apply the new discussion thread schema, and rebuild front-end assets if extractive bundling is introduced later.
