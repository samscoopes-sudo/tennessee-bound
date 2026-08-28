$OUTDIR = "channels\dave\runs\lawn-care-fall"
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null
Set-Location $OUTDIR

Write-Host "Downloading lawn care VO chunks..."

Invoke-WebRequest -Uri "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/20f508a2-2e96-4dbd-9968-bb954ccc8b79.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZQ5MV2FOF%2F20260828%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260828T115230Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEIT%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJGMEQCICGXAh4jbpo0yMLlPsn5KIujFqjcyV9w8tsMliCd%2BjM3AiBzUiMI5TlD2mtajwYTKdZx6FyFBb9WcZ3PiV0hCQhAWiqABQhNEAAaDDAyNDk0ODAzNDYxMSIM8HVI2LzVjeQzHDDMKt0EzM5EYeKPJRYgzm%2FvrHmv4WyOGThf8XFX3yPOqAhs%2B%2FCXdYgarL2wOplWF4jWHFdVFpeP9TDndAo%2Fp3Mlg0P5eUQA8HQrxovCMxp%2BnD6mhyijoIerj0Dy%2FgIOFVI7QcWBRhDnG3tpaT1R8UfgD3pH06jKlWx64wygqPSIqOtWREhakKZI3c%2Fsgy%2FPEXUrUrqfjZR4Xca1IteWUu5uFCcX0k%2FD85MX1Egv2fvhBuvcJT%2BGXi%2Fqkc2C82IuOXjMpOse07HtyV%2Frh2fEJozAybzMy%2FkSXmyjsvMfDBRNLkW5rQcQ9rBBfYIW5JpbYS3IfTYj2wNQiES8qyk%2FA2vYcj5BQ4%2FxkAYe%2FIFEZo9AycuWwP%2BdobTRHEPLzJz8g1jLQjpwEdzFtALPdNNfMY46O9H%2FxfjlsbjD1f%2FsfoLj49oEDx1yShSKOJkCH%2Bg5%2F7qKGyec03d88cIW1a9L9m8463XXQ7oSK%2FzcbhBBgklVS0cMbg3T93PdLUgnvuGvxs3OnqI4Xb6vxRIb8U47ARWHsAYsd0dmwuiMCIyVt2av1wZnstybW%2BJoa9a3JOC1h2pBYgB8St5Jw0mKzOJBAe7lc3m6T%2FhS7jxeGjAbaWx6owPJeMjQ%2FR%2FbdeO37ukBDvRrolIqPiooUL3ZwGA6UEuwQrkQW%2Ft39mPzqAETt0JnlazkSq9znJCeAzXYTtZH6l1jIum6qi1Q4u2uxt2RdJ4Uv7teNv3MjEPxXSNUz13%2BIJm4CKSlmFA4N6aKgrx8PUILlHcCabC6sdhp83e9sooiVmZGNJwwmNJP2sJmR4R1L0kw%2FuzF1AY6mQE7pGWx%2FiYlykAL9J5pw7ndFDzz1yGtyXYlN8nXP9qWXd3hulkophwJAQPdT7b86hy451CrAysrnSPVs1xAnkbxtDIs2PKmOa8AkfK3%2FF6remCAv5d2p484mofNzYTMRg7oYT4Ms7pd5d2Ggvlv0nJ8xo86%2BiZ21wmzUYc26EkpxDyGyOqLkWzr7iLmLWlQQM55VkbHAGj1mA8%3D&X-Amz-Signature=d0f80011a78edace898a79593bdc8d19e1d5fe7c5b118d05ac48f1ab5ce92c6a&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject" -OutFile "chunk0.mp3"
Write-Host "chunk0 done (3:57)"

Invoke-WebRequest -Uri "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/842c6c55-7983-40be-a99a-7f359fa74179.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZWHXVOZPB%2F20260828%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260828T115241Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEIT%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDtXHpfdBpP%2BDnvDklX1X4AuPxPGdl9HOhZ%2FqxAzjb%2FlgIhAJlabZM6kM23wRtnoHYxljVqUsdWcqOzYm8pxFe5idpOKoAFCE0QABoMMDI0OTQ4MDM0NjExIgxXzBDOnxsFpcrBGREq3QRWcUD6SRSx5EO3Ek2RrLzX5tO5An4qa2NoAjxYVUQhmv5vCMFIIxlcLiy7ALDrxHuYxWlghf8ohgEonY0NZZGJAQ2Py50B49VOUzS8cYsin1NUNmxwpUwObDENIMlqG1kp7P8R4gN7w7zI7WF7RdsuvxL57wOSQgmPnIDagBCDjjMUthl5UYwvLmpTD4WTtxBF57oOoVSQEYkbiE7iCMJipGOPHCjVhlc1LdAL5rxhCDfLwQQFvuAFMemLYiRnwTHoXWqFobma4rg3HfT4IpKOEo%2Bjg5RAbhAoSlrHmBlxVTPKidF3SZYLvThx1a8G05luDqjzKuZbChgDnYy5z%2BuGxLDFGpBdQfgNerNHPlmTUoD0NDTWtyFRIXkIaZIVJPSRL%2F%2BzD35vKP%2F5uYMiLOtf5k5ixpqE0SH3VKWv7F0x8QcJW1ZZQwAo11oN8jwL2%2BEMBq6lY2x%2BX2kCH2GA5UqOMe%2BQlv5LrNmtDZK4uOO7eYA0m29xTq%2FUGcH4W27hLj5i3bGf5DIaYwL0noTNUOYZwngZEvhiDSOauNKWizwuD8zEiYTFx2s26nlMcPvuaGDjr0am9OGn8k9TzzpTKW2Til1cxSc7%2FajdkyQH4ZtVFlzJP90G%2FI%2FTlZsVrIdN5cHqgk3xinw0CHCyLp1TTl9XDXthBsy36ds9gUZEAYM5qnOKwp8SMN8XZ5kE9O8EMAdigdzIfXet1GoVIpiKN3Pop05ARZiCzjcawzKlI8b85ZYIjBZXwlmNddzPQyrEPi2Twm4Ok%2FS97vGjnrAjYYNfqp80nKiMiOXjS0wgTzCJ7cXUBjqXASS3w2M1GjqrNbOK4wlRxtbYG08uC1mmaePF4UqKqyR72Czk3i5tf%2FYD%2FMOMt59EGhAa10JAj%2FTO4rJinF2nY%2FWvenqykWZPWcDh5dxEAIc4Nmrhi24%2BschDbaNywNgVqZMohjcBZOvGOh3UxWme%2B4N9BckhpgHKD9YcfoUbGYZKfvFK4mYOYUAopKwDgSAk0pC4qwv49wE%3D&X-Amz-Signature=170e2691dfdcabf4192421a14a090f9a209c7df7fa6e221b818743f956a50570&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject" -OutFile "chunk1.mp3"
Write-Host "chunk1 done (3:32)"

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
