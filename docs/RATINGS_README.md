# Page Relevance Ratings Documentation

This directory contains the complete analysis of BLT navigation pages based on their relevance to the core product mission as outlined in the [forum discussion](https://github.com/orgs/OWASP-BLT/discussions/5495).

## Documents

### 1. RATINGS_EXECUTIVE_SUMMARY.md (Start Here!)
**Best for:** Stakeholders, Product Managers, Leadership

Quick overview with:
- Top 20 most relevant pages to keep
- Bottom 10 least relevant pages to remove
- Impact analysis & recommendations
- Next steps

### 2. PAGE_RATINGS_SUMMARY.md  
**Best for:** Quick Reference, Team Discussions

Easy-to-scan tables:
- All pages organized by rating category
- Statistics and breakdown
- Alignment with core mission pillars

### 3. PAGE_RELEVANCE_RATINGS.md
**Best for:** Detailed Analysis, Implementation Planning

Comprehensive documentation:
- Individual rating for each page (80+ pages)
- Detailed rationale for every rating
- Recommended navigation structure
- Full categorization (Keep/Maybe/Remove)

## Rating Scale

**1-20:** Core features - Essential to main purpose  
**21-40:** Important secondary - Valuable but not core  
**41-60:** Useful features - Nice to have  
**61-80:** Peripheral - Questionable value  
**81-100:** Remove/Reconsider - Not aligned with core focus

## Core Mission (from Forum Discussion)

1. **Vulnerability Discovery** - Finding unpatched CVEs
2. **UI/UX Bug Discovery** - Internet-wide bug reporting
3. **Education & Contributor Growth** - Training
4. **Incentivizing Fixes** - Rewards for security PRs
5. **Knowledge Sharing** - Community learning

## Quick Stats

- **Total Pages Rated:** 80+
- **Core Features (1-20):** 12 pages
- **Secondary (21-40):** 17 pages
- **Evaluate (41-60):** 18 pages
- **Consider Removing (61-80):** 16 pages
- **Remove (81-100):** 10 pages

## How to Use These Ratings

1. **Start** with RATINGS_EXECUTIVE_SUMMARY.md
2. **Review** specific pages in PAGE_RATINGS_SUMMARY.md
3. **Deep dive** into rationale in PAGE_RELEVANCE_RATINGS.md
4. **Discuss** with team which pages to keep/remove
5. **Check analytics** for pages rated 41-80
6. **Plan removal** of pages rated 81-100
7. **Implement** navigation changes

## Immediate Actions Recommended

✅ **Keep & Highlight:** Pages rated 1-30  
⚠️ **Evaluate Usage:** Pages rated 41-60 (check analytics)  
❌ **Plan Removal:** Pages rated 81-100 (deprecate)

## Navigation Current Location

The main navigation sidebar is located at:
- `/website/templates/includes/sidenav.html`

## Questions?

These ratings are based on the core product focus outlined in the forum discussion. They are recommendations to guide strategic decisions about product direction and navigation simplification.

For questions or discussions about specific ratings, please refer to the detailed rationale in PAGE_RELEVANCE_RATINGS.md or discuss in the forum thread.
