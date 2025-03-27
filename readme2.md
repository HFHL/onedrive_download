拉下来后，


python batch_download_unbalanced_train.py list
列出所有批次及其包含的文件

如果能正常看到很多 .tar文件，那么就没有问题。


python batch_download_unbalanced_train.py <批次号>
例如：

python batch_download_unbalanced_train.py 1
 
python batch_download_unbalanced_train.py <批次号> <并行数量>
设置并行下载数量并下载指定批次
例如：python batch_download_unbalanced_train.py 1 5


下载过程中可能有些文件下载失败，等下载完成后，运行：

python batch_download_unbalanced_train.py verify 1
后面的数字1 是批次。

如果有缺失的文件，那么运行：

python batch_download_unbalanced_train.py missing <批次号>

例如：

python batch_download_unbalanced_train.py missing 1

---


下载完成以后，需要手动挪一下目录，保持之前的结构。

downloads/
├── a_t5/
    ├── train
        ├── 1.tar
        ├── 2.tar
        ...
    ├── step_1_unzip.py
    ├── step_2_generate_parquet.py
    ...

下载下来的文件没有train目录，就全部放到train里就行了。后面他们自己分一下也很快。


到这一步以后就按照之前的做法就可以了。