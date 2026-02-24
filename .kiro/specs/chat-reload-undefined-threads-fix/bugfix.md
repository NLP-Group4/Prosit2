# Bugfix Requirements Document

## Introduction

When reloading an old chat in the Electron desktop app, the application crashes with a ReferenceError because the topbar attempts to access an undefined `threads` variable. The component uses a `projects` state array where each project contains a `threads` array, but there is no standalone `threads` variable. This bug prevents users from successfully reloading and viewing their saved chat threads.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN an old chat is reloaded with an active thread THEN the system crashes with "ReferenceError: threads is not defined at ChatPage"

1.2 WHEN the topbar attempts to display the thread title THEN the system references an undefined `threads` variable instead of accessing the threads from the active project

### Expected Behavior (Correct)

2.1 WHEN an old chat is reloaded with an active thread THEN the system SHALL display the correct thread title in the topbar without crashing

2.2 WHEN the topbar attempts to display the thread title THEN the system SHALL find the thread from the active project's threads array in the `projects` state

### Unchanged Behavior (Regression Prevention)

3.1 WHEN no thread is active THEN the system SHALL CONTINUE TO display "New thread" in the topbar

3.2 WHEN a thread exists but has no title THEN the system SHALL CONTINUE TO display "New thread" as the fallback

3.3 WHEN switching between threads within the same project THEN the system SHALL CONTINUE TO update the topbar title correctly

3.4 WHEN creating a new thread THEN the system SHALL CONTINUE TO display "New thread" in the topbar
