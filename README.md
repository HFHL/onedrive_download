# OneDrive下载助手 - 简单好用的文件下载工具 📥

# 第一步
找到非鱼子，他会给你一些东西。

# 第二步
在当前目录创建./env文件，把非鱼子给你的东西粘贴进去。

# 第三步

运行命令


```
python browse_onedrive_with_shared.py 
```

如果是第一次运行，会弹出提示：

To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code NFXKBK8ZE to authenticate.


直接访问链接，然后复制对应的code到浏览器中。

登陆即可。

然后终端会进入一个可交互的界面，

这时候直接输入 `shared`,查看共享文件夹。


```
请输入命令: shared

=== 共享项目 ===

  1. 📂 文件夹 wesoundeffects (由 未知用户 共享)
  2. 📂 文件夹 audiocaps (由 未知用户 共享)
  3. 📂 文件夹 CLAP_audio_dataset (由 未知用户 共享)

操作:
  cd <编号> - 进入文件夹或共享项目
  cd .. - 返回上一级
  shared - 查看共享项目
  home - 返回个人根目录
  path - 显示当前完整路径
  download - 下载当前文件夹
  exit - 退出浏览器

```

输入 `cd 3`

可以看到：

```
请输入命令: cd 3

=== 共享项目: CLAP_audio_dataset ===

文件夹:
  1. 📂 BBCSoundEffects
  2. 📂 Clotho
  3. 📂 ClothoAQA
  4. 📂 ESC50_1
  5. 📂 ESC50_2
  6. 📂 ESC50_3
  7. 📂 ESC50_4
  8. 📂 ESC50_5
  9. 📂 EmoV_DB
  10. 📂 Jamendo_16bit
  11. 📂 Knocking_sounds
  12. 📂 MACS
  13. 📂 Urbansound8K
  14. 📂 VGGSound
  15. 📂 WavText5K
  16. 📂 audiocaps
  17. 📂 audioset_strong
  18. 📂 audioset_t5_debiased
  19. 📂 audioset_wavcaps
  20. 📂 audiostock
  21. 📂 audiostock-train-250k
  22. 📂 audiostock_250k
  23. 📂 bbcsoundeffects_wavcaps
  24. 📂 epidemic_sound_effects
  25. 📂 epidemic_sound_effects_t5_debiased
  26. 📂 esc50
  27. 📂 esc50_no_overlap
  28. 📂 free_to_use_sounds
  29. 📂 genius_16bit_128
  30. 📂 juno_16bit
  31. 📂 paramount_motion
  32. 📂 sonniss_game_effect
  33. 📂 sonniss_game_effects
  34. 📂 synth_instructions
  35. 📂 wesoundeffects

```

这里列举了所有的项目，然后找到要下载的项目，cd进去，

例如 `cd 31`

可以看到以下画面
```
=== 共享项目: CLAP_audio_dataset/EmoV_DB ===

文件夹:
  1. 📂 test
  2. 📂 train
  3. 📂 valid

文件:
  (无文件)

操作:
  cd <编号> - 进入文件夹或共享项目
  cd .. - 返回上一级
  shared - 查看共享项目
  home - 返回个人根目录
  path - 显示当前完整路径
  download - 下载当前文件夹
  exit - 退出浏览器


```

然后输入 download即可
```
请输入命令: download

要下载的共享文件夹信息:
驱动器ID: b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a
项目ID: 01HVJG3GYS4VEGWJTQNFDYMKLTKZXJ7EQY
请使用以下命令下载:
python onedrive_downloader_shared.py
然后输入驱动器ID和项目ID: b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a 01HVJG3GYS4VEGWJTQNFDYMKLTKZXJ7EQY

```
会告诉你用什么命令，然后对应的驱动器id和项目id，

然后退出程序，运行
python onedrive_downloader_shared.py

然后输入2

```
(base) root@autodl-container-322649a1f3-69f8bbcd:~/autodl-tmp/one_drive/onedrive_download# python onedrive_downloader_shared.py
请输入共享项目的信息:
1. 只输入项目ID
2. 输入驱动器ID和项目ID
请选择输入方式 (1/2): b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a
无效的选择
(base) root@autodl-container-322649a1f3-69f8bbcd:~/autodl-tmp/one_drive/onedrive_download# python onedrive_downloader_shared.py
请输入共享项目的信息:
1. 只输入项目ID
2. 输入驱动器ID和项目ID
请选择输入方式 (1/2): 2
请输入驱动器ID: b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a
请输入项目ID: 01HVJG3G6TO3PQXJAPGZD36OIWYWMW36YB
正在处理共享项目: WavText5K (驱动器ID: b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a, 项目ID: 01HVJG3G6TO3PQXJAPGZD36OIWYWMW36YB)
正在处理共享项目: test (驱动器ID: b!mxLvO8_fT0WFEgKhZ6yFsfp19tyWN7ZAoE_IwT5dSt66L5RtyWF7TIFo9ewM8e4a, 项目ID: 01HVJG3GZMNGXARPJS3FGJWP67ICBROF2G)
正在下载: 0.tar (470.45 MB)
```


把对应的驱动id和项目id输入进去，就会开始下载。

下载好以后，将主目录下的：
step1
step2
step3
复制到数据目录下，也就是放到和train test valid同一个目录。

然后step1，直接run
python step1_unzip.py

然后step2需要改一下，需要问ai，把step2的代码和任意一个train data里的json文件交给ai，然后问它：

```
解析出来的parquet包含哪几个字段？

{"text": "OUTLAND Places - Orgallone - Loop 019", "original_data": {"file_path": "/mnt/audio_clip/dataset_creation/raw_datasets/wesoundeffects/WeSoundEffects/Thibault Rouslet/Outland Places Orgallone/OUTLAND Places - Orgallone - Loop 019.wav"}}

这是我现在的json，请问当前代码能够正确解析吗？保持parquet的字段不变，

```

如果不能正确解析，让ai修改后返回完整代码即可。应该一次性能输出正确的代码。

然后直接run 

nohup step2_generate_parquet.py

这一步完成以后，找到非鱼子要accesstoken


然后登陆huggingface， 
输入命令：

```bash
huggingface-cli login
```

输入完成后，再执行

nohup step3_upload_data.py

