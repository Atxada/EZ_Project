# EZ Project
---

![Project_Menu_UI](/docs/Project_Menu_UI.PNG)
> **Project menu UI**

![Asset_Browser_UI](/docs/Asset_Browser_UI.PNG)
> **Asset browser UI**

---

## Description

EZ Project is a small application designed to simplify project management. The philosophy of this application is to create asset navigation as intuitively as possible, so finding the file is much more effective without the need to fiddle around with a complicated folder structure. Currently, it only supports asset files like Maya ASCII (.ma), Maya Binary (.mb), and FBX (.fbx) file formats.

**Author's note:** 
I might or might not update this application in the future, even though this application has a lot of potential and it's only the bare-bones functionality that is supported. Maybe if I have time in the future, I will keep adding new useful features. Fingers crossed! 🤞

## Features
---
- ### Customizable project and asset
  ![1 asset project customization](https://github.com/user-attachments/assets/d8eb3538-f207-4434-aab2-2ca04853eb1f)

    Differentiate between projects and assets with unique names, categories, and icons.

- ### Intuitive UI navigation

    With a deliberate design to keep menus simple and uncluttered, browsing assets is much more efficient.

- ### Assign and monitor deadline

    Set a deadline for specific assets, allowing users to see all assignments corresponding to the assigned date.
    Calendar editor will show 3 colors depending on the active assignment or active todo: orange (active assignment), blue (active todo), and green (finished assignment or todo). 
    Asset has 3 statuses: unchecked, checked and verified. If an asset is verified, the assignment is considered done.

- ### Transfer project across all users

    Using standard JSON format, the project can be shared with other users by importing the file

- ### (experimental) Take a screenshot

- ### (experimental) Automated file version control

    Updating new asset versions will automatically manage the older version in File Explorer.

- ### And many more useful features!

---

> [!NOTE]  
> Tested in Windows 10 22H2, Python 3.12.1 and Qt 6.7.1 (might not work with other OS)

> [!IMPORTANT]  
> - This project is not intended for commercial or studio use, it's only a part of my personal project.
> - I do not own any images shown in the application demo, all rights belong to its rightful artists. No copyright infringement intended.
