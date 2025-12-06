# GitHub Comment Leaderboard UI

## Visual Layout

The GitHub Comment Leaderboard appears on the Global Leaderboard page at `/leaderboard/`.

### Page Structure

The leaderboard page displays multiple leaderboard sections in a responsive grid layout:

```
┌─────────────────────────────────────────────────────────┐
│              Global Leaderboard Page                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Points     │  │  Pull        │  │  Code        │ │
│  │  Leaderboard │  │  Request     │  │  Review      │ │
│  │              │  │  Leaderboard │  │  Leaderboard │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Top Visitors │  │   GitHub     │  │ Bug Bounties │ │
│  │              │  │   Comment    │  │              │ │
│  │              │  │  Leaderboard │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### GitHub Comment Leaderboard Section

Each leaderboard card has:

```
┌────────────────────────────────────────────────┐
│     GitHub Comment Leaderboard                 │
│  ┌─────────────────────────────────────────┐  │
│  │                                         │  │
│  │  ○  username1  🔗                       │  │
│  │                      Comments: 150      │  │
│  │  ───────────────────────────────────    │  │
│  │                                         │  │
│  │  ○  username2  🔗                       │  │
│  │                      Comments: 120      │  │
│  │  ───────────────────────────────────    │  │
│  │                                         │  │
│  │  ○  username3  🔗                       │  │
│  │                      Comments: 95       │  │
│  │  ───────────────────────────────────    │  │
│  │                                         │  │
│  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

Where:
- `○` = User's GitHub avatar (circular, 44x44px)
- `username` = Clickable link to user's BLT profile
- `🔗` = GitHub icon linking to user's GitHub profile
- `Comments: X` = Total comment count badge

### Styling

The leaderboard uses Tailwind CSS with:

- **Header**: Red (#e74c3c) border, bold 3xl text
- **Cards**: Gray border, white background, rounded corners
- **Avatar**: Circular, gray border
- **Badges**: Light gray background, rounded
- **Layout**: Flexbox with gap spacing, responsive (min-width: 300px, max-width: 550px)

### Responsive Design

- **Desktop**: 3 columns side by side
- **Tablet**: 2 columns
- **Mobile**: Single column stack

### Empty State

When no data is available:
```
┌────────────────────────────────────────────────┐
│     GitHub Comment Leaderboard                 │
│  ┌─────────────────────────────────────────┐  │
│  │                                         │  │
│  │   No GitHub comment data available!     │  │
│  │         (displayed in red text)          │  │
│  │                                         │  │
│  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### Interactive Elements

1. **Username link**: Navigates to user's BLT profile (`/profile/{username}`)
2. **GitHub icon**: Opens user's GitHub profile in new tab
3. **Avatar**: Visual identification (loaded from GitHub)

### Color Scheme

Following the BLT design system:
- Primary red: `#e74c3c` (borders, accents)
- Gray tones: `gray-100`, `gray-200`, `gray-300` (backgrounds, borders)
- Text: Default dark text with hover effects

## Technical Implementation

The template uses:
- Django template tags for loops and conditionals
- Gravatar fallback for missing avatars (when user doesn't have GitHub profile linked)
- GitHub username for avatar URLs when available (e.g., `https://github.com/{username}.png`)
- Responsive Tailwind classes (`flex`, `flex-col`, `flex-wrap`, `min-w-[300px]`, `max-w-[550px]`)

## Data Flow

```
Management Command → Database → View → Template → Browser
     (fetch)      GitHubComment  (query)  (render)  (display)
```

## Accessibility

- Semantic HTML structure
- Alt text on images
- Keyboard navigable links
- Sufficient color contrast
