# Job Search Starter

A configurable job search that emails new potential matches as Excel or CSV attachments. Each person runs an independent copy with their own settings, accounts, schedule, and delivery history. No personal profile, email address, credentials, or previous search results are included.

## Create your own copy

You need Python 3.11+ locally, or a GitHub account for scheduled runs. The public starter contains code and generic examples. **Create a private repository for your working copy** so your preferences and accumulated job history stay private. Do not fork the public repository for personal use: public forks stay public.

If the starter has a **Use this template** button, select it, choose a repository name, and select **Private**. Otherwise create an empty private repository and upload these starter files, including `.github/workflows/job_search.yml`. You can also unzip the download and push it with Git. No history from the original personal project is needed.

## Set your preferences

Copy `config.example.json` to `config.json`, then edit it. The example role is a placeholder, not a recommendation.

| Setting | Meaning |
| --- | --- |
| `roles` | Required title phrases. Include title variants such as `software engineer`, `software developer`, or `engineering manager`. At least one must appear in the search result title. |
| `candidate_profile` | Experience, seniority, IC/management preference, employment type, sponsorship needs, and other context. AI uses this as preference context; it is not a guaranteed hard filter. |
| `skills`, `industries` | Preferences for AI fit notes; industries also influence generated searches. Empty means no preference. |
| `locations` | Allowed office city/region names and aliases, e.g. `New York`, `NYC`, `Brooklyn`. These are text matches, not commute-distance calculations. Empty permits any office location. |
| `arrangements` | Allowed values: `Remote`, `Hybrid`, `Onsite`. |
| `remote_region` | Where a remote job must permit working, e.g. `United States`. Without AI, this phrase must appear in the text unless unknown locations are allowed. |
| `include_unknown_location` | Whether ambiguous location/remote eligibility may pass. Default false. |
| `exclude_terms` | Hard exclusions if a phrase appears anywhere in the title or posting. Use carefully; a posting can mention a term in a different context. |
| `minimum_annual_salary` | `null` means undecided/no minimum. Otherwise compares the advertised annual base range's maximum to this number: a range overlapping your minimum can pass. |
| `salary_currency` | Currency of that minimum, e.g. `USD`. No exchange-rate conversion. |
| `include_unknown_salary` | Include missing, ambiguous, hourly, or different-currency salaries. True is useful when salary requirements are undecided. |
| `queries` | Extra literal Tavily search queries, evaluated first. Generated role/location/industry queries follow. |
| `company_domains` | Optional bare domains to search using `site:` queries, not career-page scraping. |
| `max_queries`, `max_results_per_query` | Per-run cost limits. Defaults: 12 queries, 10 results each. Extra queries beyond the limit are omitted. |
| `output_format` | `xlsx` for formatted columns, filters and a frozen header; `csv` for a portable table. History is JSON, so changing format does not reset deduplication. |
| `email_provider` | `gmail` or `resend`; explicit selection avoids accidentally sending from a fallback account. |
| `ai_model` | Anthropic model ID used only when `ANTHROPIC_API_KEY` is set. |

Role, arrangement, office-location, exclusion and salary checks run in code. AI additionally evaluates remote jurisdiction and whether a page is one open job. Preferences are not strict skill/seniority/industry filters. Read the actual posting before applying.

## Services and credentials

Search uses [Tavily](https://www.tavily.com/); create your own account and API key. Optional [Anthropic](https://console.anthropic.com/) enrichment extracts employer, salary and eligibility details. Without it, the app uses conservative title/location keywords, leaves salary unknown, and cannot reliably distinguish job listings from search pages. Set `include_unknown_salary=false` with a salary minimum only when AI is enabled, otherwise unknown salaries are all excluded.

Searches and AI calls may cost money. Preview also uses those services. Check provider pricing and account limits; no fixed free allowance is assumed. Your queries go to Tavily; when AI is enabled, the profile and retrieved posting text go to Anthropic. Email attachments go through the selected email provider.

Choose one delivery method:

* Gmail: `GMAIL_USER` and `GMAIL_APP_PASSWORD`. Use a Google app password with two-step verification, not your ordinary account password. Availability depends on account policy. See [Google's app-password instructions](https://support.google.com/accounts/answer/185833).
* Resend: `RESEND_API_KEY` and `RESEND_FROM`. Configure a permitted sender. Resend's test sender has recipient restrictions; use a verified domain for general delivery. See [Resend domains](https://resend.com/docs/dashboard/domains/introduction).

Both methods need `EMAIL_TO`. Keep all real addresses and API keys out of files committed to the public starter.

## Local setup

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.json config.json
# Edit config.json before continuing.
python job_search.py --check
```

Set credentials in the current shell (replace placeholders):

```powershell
$env:TAVILY_API_KEY = 'your-key'
$env:EMAIL_TO = 'your-address'
$env:GMAIL_USER = 'your-gmail-address'
$env:GMAIL_APP_PASSWORD = 'your-app-password'
# Optional:
$env:ANTHROPIC_API_KEY = 'your-key'
```

For Resend, select `resend` in the config and set `RESEND_API_KEY` and `RESEND_FROM` instead of Gmail credentials. On macOS/Linux use `export NAME='value'`. The script does not automatically read `.env` files.

```powershell
python job_search.py --preview
python job_search.py --test-email
python job_search.py
```

Preview writes `results/new_jobs.xlsx` and `results/master.xlsx` (or `.csv`) without emailing or modifying history. Test-email sends a test message only. A normal run searches and emails, including a zero-match summary, then saves `state/history.json`. Send failure exits unsuccessfully and leaves jobs retryable. AI/search failures also fail the run rather than claiming there were no matches.

## GitHub Actions setup

In your **private** copy, open **Settings → Secrets and variables → Actions**. Add these repository secrets:

| Secret | Value |
| --- | --- |
| `JOB_SEARCH_CONFIG` | The full contents of your edited `config.json`. |
| `TAVILY_API_KEY` | Your Tavily key. |
| `EMAIL_TO` | Your delivery address. |
| `GMAIL_USER`, `GMAIL_APP_PASSWORD` | For Gmail delivery. |
| `RESEND_API_KEY`, `RESEND_FROM` | For Resend delivery instead. |
| `ANTHROPIC_API_KEY` | Optional AI enrichment key. |

Open **Actions → Job Search → Run workflow**, first choosing `preview`. Download the `job-results` artifact and inspect it. Then choose `test-email`, and finally `search` to test the full flow.

To enable the weekly run, add a repository **variable** `ENABLE_SCHEDULE` with value `true`. Remove it or set it to `false` to disable scheduled searches. Manual runs remain available. The workflow refuses to run in public repositories, keeping private settings and results out of public logs/artifacts/history.

The default cron is Friday **13:17 UTC**: 9:17 a.m. New York during daylight saving time and 8:17 a.m. during standard time. Edit `.github/workflows/job_search.yml` for your desired time. [GitHub schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) use UTC by default and may be delayed. Scheduled workflows must be on the default branch. Account/organization Actions policy and usage limits apply.

Successful searches commit only delivery history to the private repository using the workflow token; no personal settings are committed. Results are also available as artifacts for seven days. Your Actions policy must allow write access, and branch protections must permit the bot's history commit. Runs are serialized to avoid two searches overwriting the same history.

## Troubleshooting and limitations

* **Workflow skipped:** use a private repository; scheduled runs also need `ENABLE_SCHEDULE=true`.
* **Configuration fails:** validate locally with `--check`; review JSON syntax and the setting table. Do not put comments into JSON.
* **Authentication/delivery failure:** check the selected provider and exact secret names, Gmail app-password policy, Resend sender/recipient restrictions, and provider quotas. Public logs deliberately omit raw provider errors to avoid leaking account details.
* **Push failure after delivery:** the email may have succeeded but history was not saved; retry can resend jobs. Fix Actions write permissions/branch protections before rerunning. Email and Git commits are not one atomic transaction.
* **Too few matches:** add role variants, location aliases and custom queries. Relax unknown-location handling only if you are willing to verify eligibility yourself. Long lists may exceed `max_queries`.
* **False positives:** location mentions may describe another office, remote jobs may restrict states, search snippets may be stale, and AI can make mistakes. The fallback cannot verify single-posting status or salary. This is a discovery aid, not a guarantee of eligibility or availability.
* **Duplicate/reposted jobs:** deduplication uses the exact URL without its fragment. Tracking parameters, new URLs, or alternate job boards can produce duplicates. Old delivered jobs remain in the master; no automatic removal of closed postings is included.
* **Change requirements:** old delivered URLs stay suppressed. To start over, back up then remove `state/history.json` (and commit that removal if using Actions). This can resend previous matches.

## Development

Run `python -m unittest discover -s tests -v` for offline checks. These use mocked providers and do not spend credits or send email.

The starter uses the MIT license in `LICENSE`. Publish only these clean source files. Do not upload your private working repository, `.git` history, config, generated results or state. Mark the public repository as a template in GitHub settings for easy independent private copies.
