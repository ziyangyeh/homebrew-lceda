# homebrew-lceda

非官方的 Homebrew tap，用来安装**嘉立创EDA 专业版**（LCEDA Pro / EasyEDA Pro）。

**只支持 Apple Silicon**（`depends_on arch: :arm64`）。Intel Mac 请直接去
[官网下载页](https://lceda.cn/page/download) 拿 x64 包。

官网下载页的链接需要登录才能拿到，但 CDN 直链 `https://image.lceda.cn/files/…`
是公开的，本 tap 用的就是它，下载的就是官网同一个安装包。

## 安装

```sh
brew tap ziyangyeh/lceda
brew install --cask lceda-pro
```

或者一行：

```sh
brew install --cask ziyangyeh/lceda/lceda-pro
```

Homebrew 现在对第三方 tap 有信任机制，装的时候会问一句要不要信任这个 cask，
回车确认即可。想提前一次性信任整个 tap（或者在脚本/CI 里非交互安装）：

```sh
brew trust --tap ziyangyeh/lceda
```

安装包大约 350 MB，里面是一个 dmg，cask 会自动解包、挂载，再把
`嘉立创EDA(专业版).app` 放进 `/Applications`。

专业版是用 Developer ID 签名并且经过 Apple 公证的
（`spctl -a` 结果为 `Notarized Developer ID`），所以**不需要** `--no-quarantine`，
装完直接双击就能开。万一遇到“已损坏，无法打开”，再执行：

```sh
xattr -dr com.apple.quarantine "/Applications/嘉立创EDA(专业版).app"
```

> 注：Homebrew 官方的 `easyeda` cask（标准版 6.5.x）因为过不了 Gatekeeper 检查，
> 已经在 2026-09-01 被停用。专业版没有这个问题。

## 升级

```sh
brew update && brew upgrade --cask lceda-pro
```

软件自带的“检查更新”在 macOS 上只会把新安装包下载到
`~/.config/LCEDA-Pro/updater` 然后在访达里打开，还是要手动拖一遍，
所以建议在设置里关掉它，统一用 `brew upgrade` 管理。

## 卸载

```sh
brew uninstall --cask lceda-pro          # 只删应用
brew uninstall --zap --cask lceda-pro    # 连配置、缓存一起删
```

`--zap` 会清掉 `~/.config/LCEDA-Pro` 和 `~/Library` 下的相关文件，
但**不会动 `~/Documents/LCEDA-Pro`**——工程、元件库和本地数据库都在那里。

## 自动更新

| workflow | 触发 | 作用 |
|---|---|---|
| [`update-cask.yml`](.github/workflows/update-cask.yml) | 每天 02:20（北京时间）+ 手动 | 抓官网下载页的最新 arm64 版本号 → 改 cask → **先验后提交** |
| [`ci.yml`](.github/workflows/ci.yml) | push / PR + 手动 | 在 macOS runner 上跑 `brew style` 和 `brew audit`，手动触发时还能真装一遍 |

tap 没有「发布」这个动作——`brew` 直接读 `main` 上的 `Casks/lceda-pro.rb`，
所以改完推上去就等于发布了。`update-cask.yml` 跑的顺序是：

```
抓版本 → 改 version + sha256 → brew style → brew fetch（下包核对 sha256）
       → brew audit → 全绿才 commit + push
```

任何一步红了就 job 失败，`main` 一个字都不会动，坏掉的 cask 进不去。

手动触发时有两个开关：

- **full-download**：本地完整下载算 sha256，而不是读 CDN 响应头里的
  `x-obs-content-sha256`（默认读响应头就够了，反正后面 `brew fetch`
  会拿真实文件核对一遍；该响应头和文件实际 sha256 一致这点已经验证过）；
- **force**：版本没变也重写一遍 version 和 sha256。

本地也能跑同一个脚本：

```sh
python3 scripts/update_cask.py --check-only   # 只看有没有新版本
python3 scripts/update_cask.py                # 有新版就改 Casks/lceda-pro.rb
python3 scripts/update_cask.py --trust-header # 用响应头里的 sha256，不下载
```

脚本只依赖 Python 3 标准库。默认会把安装包流式下载一遍算 sha256，并和响应头里的
`x-obs-content-sha256` 对比，不一致就报错退出。

## 说明

本仓库与嘉立创 / 立创EDA 官方无关，只是把公开的安装包包装成 cask。
软件本身的授权条款以安装包内的 EULA 为准。
