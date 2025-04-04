# AI Scribe Reformatter

A tool to reformat the ai consultation notes produced by heidi the AI scribe tool. This tool is not affiliated with the Heidi organisation, all trademarks and copyrights belong to them.

This tool copies a consultation, shows an editor, and then will paste it into SystmOne.

## Video Instructions

[![Watch the video](https://img.youtube.com/vi/I1D9TbiHQSs/hqdefault.jpg)](https://youtu.be/I1D9TbiHQSs)

## Instructions

* Download the latest version from the releases section on the right
* Move the file to somewhere you'll be able to find it again for the next time you want to use it (eg: your desktop)
* Double click the file you downloaded to launch it. You should see a chequered icon in your system tray (the area just next to clock in the bottom right of your screen, it might be hidden in the extra menu which looks like an up arrow)
* Middle click on a consultation formatted with the H&P template to copy it. If the tool can recognise it then a consultation editor should pop up.
* Select which sections you want to copy to Systmone and then press Ok
* Middle click the History box in your Systmone consultation and the tool will paste in the sections
* (Optional) - Sometimes if you have issued a prescription, this will prevent the Plan from being input. If this happens you should middle click on the Plan box after.

## TODO

* Extra spaces in sub-bullet point lists
* Numereical lists in plan
* Investigations into the history section

## Payment

This tool is provided freely, but I encourage you to consider subscribing to Heidi. Although this tool works with the free version of Heidi, they require subscribers to keep offering the free version, and their paid product adds the ability to query the consultationn directly to produce reports, referrals and useful targetted summaries (eg: medication change list for patient). I think it is the most useful AI innovation to come to primary care so far.

## Is this tool safe?

This question has two parts - is it safe to run on any computer, and is it safe to use with patient data?

I am an NHS GP, not a software engineer/developer, but this tool has been created with information governance in mind. The tool does not communicate with the internet in any way. I haven't added an auto-update feature for this reason. You can be confident that no patient data is leaving your computer when using it. Patient data does pass through the tool - you're copying a consultation from Heidi to SystmOne, and the tool uses your clipboard to do this. 

The aim of the tool is to reformat the data, but if there is an atypical consultation from Heidi, or they change their formatting (they do do this), some of your consultation might be missed. You *have* to read through the notes it generates to make sure it accurately reflects all of your consultation. I can't take responsibility for any omissions or inaccurate restructuring. If this seems too risky for you, then I would encourage you not to use the tool. 

I have provided all of the source code (the programming) for the tool, so you can either edit it yourself to customise it, or turn it into your own executable file. The executables are generated using pyinstaller with a github workflow. [You can see how this is done here](.github/workflows/make_exe_pyinstaller.yml). Currently it runs well through virustotal.com, although at the time of writing 2 of the 40-something virus detection heuristic algorithms flag up the pyinstaller build.
