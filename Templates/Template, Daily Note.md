up:: [[Calendar]]
dates:: {{date}}
mood:: No Data
energy:: No Data
focus:: No Data

---
# {{date:YYYY-MM-DD}}

## Wind Up
- What am I looking forward to today?
- What might challenge me today?
- What will I do if I feel anxious/stressed/worried today?
- What am I avoiding/anxious about?

## Log


## Scratchpad
- I am thinking about 


---

## Wind Down
- I am grateful for
- Today I accomplished (What did you do to work towards your goals)
- Today I spoke with 
- Today I wish I had 
- Today I enjoyed 

--- 
> [!info]
> Below are the notes which were created on this date.

```dataview
table file.mtime as "Notes Created Today" FROM "Notes" WHERE dateformat(file.ctime, "yyyy-MM-dd") = "{{date:YYYY-MM-DD}}"
SORT file.mtime DESC
```