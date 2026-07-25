<p align="center">
  <img src="loyan/res/resource/Loyan.svg" alt="LoyanBot" width="200" />
</p>

<h1 align="center">洛颜 LoyanBot</h1>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README_zh-CN.md">简体中文</a> |
  <a href="README_zh-TW.md">繁體中文</a> |
  <a href="README_RU.md">Русский</a> |
  <a href="README_FR.md">Français</a> |
  <a href="README_KO.md">한국어</a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-8ecac8?logo=python&logoColor=white" alt="Python" /></a>
  <img src="https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-8ecac8" alt="Platform" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-8ecac8" alt="License" /></a>
  <a href="https://pypi.org/project/loyan/"><img src="https://img.shields.io/badge/Version-v0.1.dev0-8ecac8" alt="Version" /></a>
  <img src="https://img.shields.io/badge/Deploy-Docker%20|%20pip%20|%20uv-8ecac8" alt="Deploy" />
</p>

<!-- STATS_CARD_START -->
<table style="border:1px solid #ddd;padding:10px 14px;max-width:460px;margin:16px auto;background:#fef5e7;">
<tr><td colspan="4" style="text-align:center;font-size:15px;font-weight:600;color:#222;padding-bottom:8px;">Source Code Stats</td></tr>
<tr><td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">Python</td><td style="padding:2px 0;width:200px;"><table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:#8ecac822;"><tr><td style="width:95.9%;height:14px;background:#8ecac8;padding:0;border:none;"></td><td style="padding:0;border:none;"></td></tr></table></td><td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">95.9%</td><td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">21,929</td></tr>
<tr><td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">React JSX</td><td style="padding:2px 0;width:200px;"><table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:#8ecac822;"><tr><td style="width:2.1%;height:14px;background:#7abfbc;padding:0;border:none;"></td><td style="padding:0;border:none;"></td></tr></table></td><td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">2.1%</td><td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">481</td></tr>
<tr><td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">TypeScript</td><td style="padding:2px 0;width:200px;"><table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:#8ecac822;"><tr><td style="width:0.7%;height:14px;background:#66b4b0;padding:0;border:none;"></td><td style="padding:0;border:none;"></td></tr></table></td><td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">0.7%</td><td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">157</td></tr>
<tr><td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">JavaScript</td><td style="padding:2px 0;width:200px;"><table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:#8ecac822;"><tr><td style="width:0.3%;height:14px;background:#52a9a4;padding:0;border:none;"></td><td style="padding:0;border:none;"></td></tr></table></td><td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">0.3%</td><td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">60</td></tr>
<tr><td style="text-align:right;padding:2px 8px;color:#555;white-space:nowrap;font-size:13px;">JSON</td><td style="padding:2px 0;width:200px;"><table cellpadding="0" cellspacing="0" style="width:200px;height:14px;border:none;background:#8ecac822;"><tr><td style="width:1.0%;height:14px;background:#3e9e98;padding:0;border:none;"></td><td style="padding:0;border:none;"></td></tr></table></td><td style="text-align:right;padding:2px 6px;color:#888;font-size:12px;white-space:nowrap;">1.0%</td><td style="text-align:right;padding:2px 6px;color:#999;font-size:12px;white-space:nowrap;">233</td></tr><tr><td colspan="4" style="text-align:center;font-size:13px;color:#888;padding-top:8px;border-top:1px solid #eee;"><b style="color:#333;">22,860</b> total · <b style="color:#333;">5</b> languages</td></tr>
</table>
<!-- STATS_CARD_END -->

A multi-platform chatbot framework for LLMs. Connect to various large language models via multiple instant messaging apps — QQ, WeChat, Telegram, Discord, and more. 😄 Extensible with plugins and modules. 👍 Built on Python 3.11+ with a Quart-based web panel. Beginner-friendly — learn plugin development quickly. 🎉


We are developing LoyanBot, and it will take several more months before it is truly ready for production deployment. Currently implemented features:

<table>
<tr><th bgcolor="#8ecac8"><font color="white">Category</font></th><th bgcolor="#8ecac8"><font color="white">Status</font></th></tr>
<tr bgcolor="#f0fff0"><td>Basic plugin system</td><td>✅ Done</td></tr>
<tr bgcolor="#f0fff0"><td>Basic lifecycle management</td><td>✅ Done</td></tr>
<tr bgcolor="#f0fff0"><td>Complete pipeline scheduling</td><td>✅ Done</td></tr>
<tr bgcolor="#f0fff0"><td>Freshly developed AI brain engine</td><td>✅ Done</td></tr>
<tr bgcolor="#e8f4ff"><td>Panel</td><td>🔄 In planning</td></tr>
<tr bgcolor="#e8f4ff"><td>Memory and context management</td><td>🔄 In planning</td></tr>
<tr bgcolor="#f5f5f5"><td>Complete Agent system</td><td>⏳ Pending</td></tr>
</table>

This project is migrated from the GracyBot project under the same organization, built upon the original core. The license has been changed from MIT to GPL-3.0. The final copyright of this project belongs to the MiniYv-IT2 organization and MiniYv.
