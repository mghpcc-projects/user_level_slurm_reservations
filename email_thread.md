```
Add read from node and switch info check
for node isolation switch commands generated
from database.



On Thu, Apr 6, 2017 at 10:23 PM, Chris Hill <cnh@mit.edu> wrote:
> scontrol -o show node=node[092,094,095,096,097,098,099,102,112,114,116,118,119]
>
> On Thu, Apr 6, 2017 at 10:22 PM, Chris Hill <cnh@mit.edu> wrote:
>> node112
>> node114
>> node116
>> node118
>> node119
>>
>>
>> On Thu, Apr 6, 2017 at 10:14 PM, Chris Hill <cnh@mit.edu> wrote:
>>> Also figure out if can get 8 from rack 9
>>>
>>> scontrol -o show node=node[091-108] | grep -v Reason | grep CPUAlloc=0  | wc
>>>
>>>  15     510    8145
>>>
>>>
>>> and 8 from rack10
>>>
>>> scontrol -o show node=node[109-126] | grep -v Reason | grep CPUAlloc=0  | wc
>>>
>>>       9     306    4896
>>>
>>> Chose 8 extra from rack 9 and 5 extra from rack 10 and create second
>>> group reservation.
>>>
>>> scontrol -o show node=node[091-108] | grep -v Reason | grep CPUAlloc=0
>>> | grep -v node101  | head -8 | awk -F= '{print $2}' | awk '{print $1}'
>>>
>>> node092
>>> node094
>>> node095
>>> node096
>>> node097
>>> node098
>>> node099
>>> node102
>>>
>>> scontrol -o show node=node[109-126] | grep -v Reason | grep CPUAlloc=0
>>>  | awk -F= '{print $2}' | grep -v node101 | awk '{print $1}'  | head
>>> -5
>>>
>>> node112
>>> node114
>>> node116
>>> node117
>>> node118
>>>
>>> scontrol -o show node=node[092,094,095,096,097,098,099,102,112,114,116,117,118]
>>>
>>> On Thu, Apr 6, 2017 at 10:00 AM, Chris Hill <cnh@mit.edu> wrote:
>>>> Next we need to regenerate the command pool for the
>>>> base reservation.....
>>>>
>>>> On Thu, Apr 6, 2017 at 9:51 AM, Chris Hill <cnh@mit.edu> wrote:
>>>>> o sometime later check what has drained
>>>>>
>>>>> scontrol -o show nodes=node[055-126] | grep -v Reason | grep  CPUAlloc=0 | wc
>>>>>
>>>>> o are there any nodes in rack 10 yet (first request)
>>>>>
>>>>> scontrol -o show nodes=node[109-126] | grep -v Reason | grep  CPUAlloc=0
>>>>>
>>>>> o yes
>>>>>
>>>>> NodeName=node117 Arch=x86_64 CoresPerSocket=8 CPUAlloc=0 CPUErr=0
>>>>> CPUTot=16 CPULoad=0.44 AvailableFeatures=node117,centos6
>>>>> ActiveFeatures=node117,centos6 Gres=(null) NodeAddr=node117
>>>>> NodeHostName=node117 Version=16.05 OS=Linux RealMemory=64000
>>>>> AllocMem=0 FreeMem=53500 Sockets=2 Boards=1 State=MAINT
>>>>> ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
>>>>> BootTime=2017-04-05T16:42:22 SlurmdStartTime=2017-04-05T16:44:31
>>>>> CapWatts=n/a CurrentWatts=0 LowestJoules=0 ConsumedJoules=0
>>>>> ExtSensorsJoules=n/s ExtSensorsWatts=0 ExtSensorsTemp=n/s
>>>>>
>>>>> NodeName=node118 Arch=x86_64 CoresPerSocket=8 CPUAlloc=0 CPUErr=0
>>>>> CPUTot=16 CPULoad=2.43 AvailableFeatures=node118,centos6
>>>>> ActiveFeatures=node118,centos6 Gres=(null) NodeAddr=node118
>>>>> NodeHostName=node118 Version=16.05 OS=Linux RealMemory=64000
>>>>> AllocMem=0 FreeMem=53616 Sockets=2 Boards=1 State=MAINT
>>>>> ThreadsPerCore=1 TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A
>>>>> BootTime=2017-01-12T07:36:43 SlurmdStartTime=2017-01-31T15:36:22
>>>>> CapWatts=n/a CurrentWatts=0 LowestJoules=0 ConsumedJoules=0
>>>>> ExtSensorsJoules=n/s ExtSensorsWatts=0 ExtSensorsTemp=n/s
>>>>>
>>>>>
>>>>> o now add one of those to existing reservation
>>>>>
>>>>> scontrol show reservation=flexalloc_moc_20170125
>>>>> ReservationName=flexalloc_moc_20170125 StartTime=2017-02-02T09:52:51
>>>>> EndTime=2018-02-02T09:52:51 Duration=365-00:00:00
>>>>>    Nodes=node[091,093,113,115] NodeCnt=4 CoreCnt=64 Features=(null)
>>>>> PartitionName=(null) Flags=MAINT,IGNORE_JOBS,SPEC_NODES
>>>>>    TRES=cpu=64
>>>>>    Users=root Accounts=(null) Licenses=(null) State=ACTIVE
>>>>> BurstBuffer=(null) Watts=n/a
>>>>>
>>>>> scontrol update reservation=flexalloc_moc_20170125
>>>>> Nodes=node[091,093,113,115,117]
>>>>>
>>>>> o and remove from drain reservation
>>>>>
>>>>> scontrol update reservation=flexalloc_cnh_MOCprep_20170406
>>>>> Nodes=node[055-116,118-126]
>>>>>
>>>>> o and set reason on node117
>>>>>
>>>>> scontrol -o show node=node091
>>>>> NodeName=node091 CoresPerSocket=8 CPUAlloc=0 CPUErr=0 CPUTot=16
>>>>> CPULoad=N/A AvailableFeatures=node091,centos7
>>>>> ActiveFeatures=node091,centos7 Gres=gpu:1 NodeAddr=node091
>>>>> NodeHostName=node091 Version=(null) RealMemory=64000 AllocMem=0
>>>>> FreeMem=N/A Sockets=2 Boards=1 State=MAINT*+DRAIN ThreadsPerCore=1
>>>>> TmpDisk=0 Weight=1 Owner=N/A MCS_label=N/A BootTime=None
>>>>> SlurmdStartTime=None CapWatts=n/a CurrentWatts=0 LowestJoules=0
>>>>> ConsumedJoules=0 ExtSensorsJoules=n/s ExtSensorsWatts=0
>>>>> ExtSensorsTemp=n/s Reason=cnh_reservation_flexalloc_moc_20170125
>>>>> [root@2017-03-07T20:40:38]
>>>>>
>>>>> scontrol -o update node=node117
>>>>> Reason="cnh_reservation_flexalloc_moc_20170125
>>>>> [root@2017-03-07T20:40:38]"
>>>>>
>>>>>
>>>>>
>>>>> On Thu, Apr 6, 2017 at 6:18 AM, Chris Hill <cnh@mit.edu> wrote:
>>>>>> Steps, part 1
>>>>>>
>>>>>> 1 - parse Peters email
>>>>>>
>>>>>> 2 - create temp reservation to drain eligible nodes (some already in Res
>>>>>> so skip those)
>>>>>> scontrol -o show nodes=node[055-072,073-090,091-109,110-126] | grep -v
>>>>>> Reason | wc
>>>>>>      41    1394   22572
>>>>>>
>>>>>> 3 - scontrol create reservation=flexalloc_cnh_MOCprep_20170406
>>>>>> nodes=node[055-072,073-090,091-109,110-126] starttime=now
>>>>>> duration=365-00:00:00 users=root,cnh flags=maint,ignore_jobs
>>>>>>
>>>>>>
>>>>>>
>>>>>> On Tue, Apr 4, 2017 at 4:28 PM, Krieger, Orran <okrieg@bu.edu> wrote:
>>>>>>> Thanks Chris, if you need any clarification, feel free to call.  The team
>>>>>>> can work any hours, so please let us know what you can accommodate.
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> From: <christophernhill@gmail.com> on behalf of Chris Hill <cnh@mit.edu>
>>>>>>> Reply-To: "cnh@mit.edu" <cnh@mit.edu>
>>>>>>> Date: Monday, April 3, 2017 at 11:12 AM
>>>>>>> To: Peter Desnoyers <pjd@ccs.neu.edu>
>>>>>>> Cc: Gene Cooperman <gene@ccs.neu.edu>, "Krieger, Orran" <okrieg@bu.edu>,
>>>>>>> "Kaynar, Emine, Ugur" <ukaynar@bu.edu>, MAniA Abdi
>>>>>>> <mania.abdi287@gmail.com>, Mohammad Hossein Hajkazemi <hajkazemi@gmail.com>
>>>>>>> Subject: Re: Progress on cache tiering
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> just parsing this now!
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> Chris
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> On Fri, Mar 31, 2017 at 1:26 PM, Peter Desnoyers <pjd@ccs.neu.edu> wrote:
>>>>>>>
>>>>>>> The team has made good progress and is now ready to exploit additional
>>>>>>> infrastructure.  The minimal configuration that they will need is 16 nodes
>>>>>>> with 8 of them on each of two racks where we have cache nodes.  The more
>>>>>>> resources that could be obtained the more compelling the paper will be, and
>>>>>>> the team is willing to work odd hours, nights, weekends… if there are
>>>>>>> windows of time that resources are available.  The minimal practical window
>>>>>>> size is 4 hours.
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> They currently have 4 nodes 91 (on rack 9) and 113-115 (on rack 10).
>>>>>>> Possible nodes they could use would be 55-72 (rack 7), 73-90 (rack 8),
>>>>>>> 91-109 (rack 9), 109-126 (rack 10).
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> The paper deadline they’re working towards is 4/21.
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> While it looks like everything is functioning and performing well, it is
>>>>>>> likely that as they run scalability experiments they will hit additional
>>>>>>> problems.
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> How is this?
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> 24/7 - existing 4 nodes, plus 1 more on rack 10 (some of these to continue
>>>>>>> after 4/21)
>>>>>>>
>>>>>>> 6 hrs/day(or night) - 16 nodes (8 * 2 racks) - starting ASAP
>>>>>>>
>>>>>>> Preferably week of 4/10-4/16:
>>>>>>>
>>>>>>> 2 8-hour slots - 32 nodes (8 * 4 racks)
>>>>>>>
>>>>>>> 2 8-hour slots - 32 nodes (16 * 2 racks)
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>> .....................................................................
>>>>>>>
>>>>>>>   Peter Desnoyers                                  pjd@ccs.neu.edu
>>>>>>>
>>>>>>>   Northeastern Computer & Information Science      (617) 373-8683
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>>
>>>>>>>
```
