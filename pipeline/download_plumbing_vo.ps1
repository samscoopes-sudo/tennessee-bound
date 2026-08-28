$OUTDIR = "channels\tennessee-bound\runs\plumbing-tips"
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null
Set-Location $OUTDIR

Write-Host "Downloading plumbing VO chunks..."

Invoke-WebRequest -Uri "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/d65c9a11-339c-40e2-a924-4d347f82a92b.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZV3QGBWMQ%2F20260828%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260828T073059Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEID%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQCrHLsiAAdwCL8P6eWuYYfuIh6nD0l7G%2FW9BQ9ZztoXVwIhAKs2UyvZLko4NrPnDXFPnMPrvS2mPZ4GtbxmyVM%2FfcasKoAFCEkQABoMMDI0OTQ4MDM0NjExIgw0BfhHfZHDTOgJ92sq3QQ%2FK%2Fre1lTaNWohKjK2%2FLsPSA%2BUJwkin0EzebUmCUvvNCdxZLUbrWHGNVKAHVITObBvkVzxUG1PB54mw5OfolE3%2BN7RD1tazUQ28MJf5MFEk44Nw6vhtv2fcdXByXdioLqaqZbLkSgiNDk14h6afaWd8t8mAm88YiPSrxQjIzk9PwrrMOimXrUdeyoATK6Cni2zSfC%2Bv36weKI13HdULBqcsepSOuzF45KRifHOrMs6P9vuWYpDQjJtpovxyYE4nHKLkISzCG8BVdvMehkwZKCNh6%2B6ZhqV%2BYkc2Pget1%2BlYDfhDvdT4WAwbdJcL7bq7NYK9EndP0FJOIJ5%2FUdB0R%2Br8%2FRwsBJvBw4nfxD6BkyMWyEH2FWc2kMxbIebZ1IX9g7ZBfoB8zWwjTimiCKX7l2LGTtv3Wf5sVgnSY%2Fz9fKe05bvPkZRkpYK9Msd1uHqT42rpsT%2FionRxmDnUo%2F3Hzi%2BL482Spb3gS9fhyj2tZfdEpozfW1IaCTpfK%2Fg3qkktE%2Fc7lWGc43mQ0xuZfP%2FiWKrFRuEOM5LlLsaDs2SyiCGaWlZbF9ywDXdAnumoGbwjqgOH4wTjhs54tm8K%2FG8igvtZpEveqktbl9wQ3OnGsmCd3Th9eWoGQRx2mUSYLF0yv5phLXol8SCOwRW8kjq2Vabj%2F4%2FuOVSVFyBbccKLW69Bk4GnHDgk61l%2Bm0yUJMpp2LIxyXAV2%2BdZD7FTEv%2F7JfOnHO0sVCN2uFUOXzjYpUEG1%2BXY%2BEqVUXNWc5UY21XAA%2B2VSC4rdWMy0JnxJsUBv2jCwChB99vdzEevF5yvzCz8sTUBjqXATZA6DIqA3KgFlATjptP6NRTw7x3boOkMuT%2FXvTbjMwM%2FJjBfpmuVPWXmI3NdKwfYsH6VD6YRBKFI6wdfEPFS0mvAYGp%2BdA3PthoFQhep6%2B9iZULgV3Vw%2FlR%2BlQhel7to0VESYJholKUq8v4q4x7Ekc%2B%2BexMHteQaU9A1p0Ka%2BSe2SE2kVloIuYi0Rl6IVGqZchatm9csIE%3D&X-Amz-Signature=fb94930a6b1fcadfe3b718f501c6e0383079b59c5d5ba23c72c52e4391ab0a4c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject" -OutFile "chunk0.mp3"
Write-Host "chunk0 done (4:33)"

Invoke-WebRequest -Uri "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/116fc3a8-c959-48e1-8fd8-07c412595a31.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZWORSY32I%2F20260828%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260828T073059Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEID%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIExnQ%2BNTFT8x1ubcK%2B4KU%2FpTX9hMRgd6ADbNff2rqrGHAiEArGR2CVrfQCILw3Lc2w7ueTP5adUS0mYeQpQ9Kzqlh3UqgAUISRAAGgwwMjQ5NDgwMzQ2MTEiDN0TkWCrkOYxwvoZ%2BirdBL4ivt0%2B%2BrB%2F3DCIZsF6%2BvwoRq%2BYvmK%2Bt%2F4SoRte0N2cbIPe44EARHP4GM4ux4I23bBN1O3buhAYjh5ZDvWC6oTeyV7veaIM50ZtmXiHZLX8lcyvnVSq7qMYEOoP2TBXo7ubIz5S0BQECwwYjRBOJs3Y4%2BK%2FV1Xms9osoF5nEpUWxXPl6z4Om%2FQpO355sc0%2F%2FBs5r91qQvSXlMekuf5%2FQ2YftU%2BmWl6MR%2FUUR7CSFEDdB3iU0p%2BiSAf10mIBsp7DdzwGDjmcqTA%2BpKR3ShFNLn3w6c4D%2FfhaHoz7l8daVw%2FLQQY0zWDrEDY6ml53KQNMtdQCjWTEFTctXQpoQVCpML3CqomSeF76F9Z4KB6kmNJboRzlbwBq08bbZWjXQG7WGcxgwk5H8xIt1Xu9FbCy1tpNdyQnmEkIh707k7ubFZu%2BxbN2KXpbxhnSt%2FfCF%2B7tuaNYOU1AdkmDX9cpTYj5brH%2F5xyM2kt%2BFvlEjGJMZokD1jQC7lgRXT14rLaU8tOfLAHZXCYk5lbJdz5HUeFbUhwtT4ImYZLgJFBrIEixDe4x01LdlgNw3UGLpLX0GhkX8mctd2rxGetOYRBGEdf9j%2B4hXdzq2tb9q9MipdvOeyTUV0Yed%2Bm%2FHMvZNvMBPkWDE2gh6futQwf34TbgQhpAHhweqNiSYhwxypyXrSlkMSs1elRwFj7fyJNXFeDNLHZGyHuTEDAPnbi04EcSpBum1Cqs%2F5XVRYlE8yd22iW6BuCwRvYWgwjxb0uJ5um7aGTL%2BpoawRJY%2Fc02d%2B6sUFtQQoEi4JRCb1C2qzQXWItZMLPyxNQGOpgBYnd5pAhHwM91mdJc6RMX64ECrDwvoPRJ0MET8KddbjjOR7o4BLzAN%2Fit9E7KUbb2lwvmBTzo1pC%2BLxSD8p6oM66XJjYFr2eodg6bo1cC3lr3Duc%2FUstTTTVKPWYSF3VdwrzI8hgayF2FSkZ1pp1a1nmvkIVVwP7HGfY%2FI4g6%2Fh%2F2dvmireIhFBLuMCp9IXpYkm3BMKKv720%3D&X-Amz-Signature=604563c5acf84d62886f43d5aed773029fa7e6188ea5300f062728555e39dff3&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject" -OutFile "chunk1.mp3"
Write-Host "chunk1 done (3:55)"

Write-Host "Concatenating into vo.wav..."
python -c @"
from pydub import AudioSegment
import glob
chunks = sorted(glob.glob('chunk*.mp3'))
combined = AudioSegment.empty()
for c in chunks:
    seg = AudioSegment.from_mp3(c)
    combined += seg
    print(f'  {c}: {len(seg)/1000:.1f}s')
combined.export('vo.wav', format='wav')
print(f'vo.wav created: {len(combined)/1000:.1f}s ({len(combined)/1000/60:.1f} min)')
"@
Write-Host "Done!"
