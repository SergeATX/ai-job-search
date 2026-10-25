# Job Application Assistant

> **Profile data:** personal files are not stored in this repo. Run `jobsearch where --assist` once (if `jobsearch` is not on PATH, use `<repo>/bin/jobsearch`) and call the printed folder `<ASSIST>`; every `<ASSIST>/...` path below lives there. If it reports no profile, tell the user to run `jobsearch register NAME PATH --default` and then `jobsearch assist-init` (copies the blank templates into `<ASSIST>`). Never write personal data into this repo.


**name:** job-application-assistant
**description:** Assists with job applications: evaluating job postings, tailoring CVs, writing cover letters, and preparing for interviews. Triggers on keywords like: job posting, job application, CV, cover letter, resume, interview prep, job fit, career, application, apply, ansøgning, stilling
**allowed-tools:** Read, Glob, Grep, WebFetch, WebSearch, Edit, Write, AskUserQuestion

---

## Workflow

When the user provides a job posting (URL or text), follow this workflow:

### Step 1: Research & Evaluate Fit
- Fetch the job posting content (use WebFetch for URLs)
- Analyze the posting for required competencies, keywords, and priorities
- Research the company (website, LinkedIn, mission, recent news)
- Score the posting against the candidate's profile using the framework in `<ASSIST>/04-job-evaluation.md`
- Present the evaluation table and verdict
- Suggest whether the candidate should call the employer before applying (see `<ASSIST>/04-job-evaluation.md` for guidance)
- Ask the user if they want to proceed with an application

### Step 2: Tailor CV
- Read the most relevant existing CV variant from `cv/` as a starting point
- Follow the guidelines in `<ASSIST>/05-cv-templates.md`
- Create `cv/main_<company>.tex` with tailored content
- Adjust: profile statement, skills section, experience bullet emphasis, section order

### Step 3: Write Cover Letter
- Follow the writing style rules in `<ASSIST>/03-writing-style.md` (critical: no em-dashes, no cliches)
- Follow the template structure in `<ASSIST>/06-cover-letter-templates.md`
- Create `cover_letters/cover_<company>_<role>.tex`
- Ensure the letter connects specific experience to the role requirements

### Step 4: Interview Preparation
- Follow the framework in `<ASSIST>/07-interview-prep.md`
- Prepare STAR-format answers for likely questions
- Identify role-specific talking points
- Draft questions the candidate should ask the interviewer

---

## Reference Files

| File | Purpose |
|------|---------|
| `<ASSIST>/01-candidate-profile.md` | Education, experience, skills, publications, awards |
| `<ASSIST>/02-behavioral-profile.md` | Behavioral assessment, strengths, ideal environments |
| `<ASSIST>/03-writing-style.md` | Tone, structure, do's and don'ts |
| `<ASSIST>/04-job-evaluation.md` | Scoring framework for job fit |
| `<ASSIST>/05-cv-templates.md` | LaTeX CV structure and tailoring rules |
| `<ASSIST>/06-cover-letter-templates.md` | LaTeX cover letter structure and tailoring rules |
| `<ASSIST>/07-interview-prep.md` | STAR examples, tough questions, roleplay guidelines |

---

## Quick Commands

The user may also ask for individual steps without the full workflow:
- "Evaluate this job posting" - Step 1 only
- "Write a CV for [company]" - Step 2 only
- "Write a cover letter for [role] at [company]" - Step 3 only
- "Help me prepare for an interview at [company]" - Step 4 only
- "What jobs should I look for?" - Career strategy discussion using profile + evaluation framework
