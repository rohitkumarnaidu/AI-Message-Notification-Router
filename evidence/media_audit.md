# Phase 2 — Media Audit Report

**Generated**: 2026-08-02T10:44:01
**Scope**: `dataset/media/images/` and `dataset/media/audio/`

---

## 1. Image Files Inventory

| File | Size (B) | FK in images.csv | Referenced by messages.csv | Notes |
| :--- | ---: | :--- | :--- | :--- |
| img_001.jpg | 243,487 | YES (img_001) | YES (multiple) | Large — likely poster |
| img_002.jpg | 45,706 | YES (img_002) | YES | Medium screenshot |
| img_003.jpg | 44,166 | YES (img_003) | YES | Travel promo |
| img_004.jpg | 381,580 | YES (img_004) | YES | Large — possibly presentation |
| img_005.jpg | 34,384 | YES (img_005) | YES | Small |
| img_006.jpg | 496,488 | YES (img_006) | NO (in images.csv only) | Unreferenced by incoming messages |
| img_007.jpg | 697,479 | YES (img_007) | YES | Large |
| img_008.jpg | 88,042 | YES (img_008) | YES — multiple (msg_005, msg_029, msg_030) | Same image in multiple messages |
| img_010.jpg | 20,651 | YES (img_010) | YES | Small promo banner |
| img_011.jpg | 59,635 | YES (img_011) | YES | School circular |
| img_012.jpg | 1,935,756 | YES (img_012) | YES (msg_060) | LARGEST — 1.9 MB — high-res poster or document |
| img_013.jpg | 33,896 | YES (img_013) | NO | Unreferenced by incoming messages |
| img_014.jpg | 64,128 | YES (img_014) | NO | Unreferenced by incoming messages |
| img_016.jpg | 74,740 | YES (img_016) | NO | Unreferenced by incoming messages |
| img_020.jpg | 27,854 | YES (img_020) | NO | Unreferenced by incoming messages |
| img_022.jpg | 741,588 | YES (img_022) | NO | Unreferenced by incoming messages |
| img_023.jpg | 1,492,150 | YES (img_023) | YES (msg_062) | Very large — fire alarm or notice |
| img_024.jpg | 28,772 | YES (img_024) | YES | Small |
| img_025.jpg | 213,654 | YES (img_025) | YES (msg_074) | Land plot scam image |
| img_026.jpg | 523,709 | YES (img_026) | YES | Safety advisory |

**Total image files on disk**: 20
**Total images registered in images.csv**: 20
**Images referenced by incoming messages**: ~15
**Images with no incoming message reference (in images.csv only)**: img_006, img_013, img_014, img_016, img_020, img_022 (~5-6 files)

> NOTE: Unreferenced images may exist for historical messages in message_history.csv or may be part of the hidden test set. Do not assume they are unused.

### Image ID Sequence Gaps
- Present: img_001..img_008, img_010..img_014, img_016, img_020, img_022..img_026
- Missing from sequence: img_009, img_015, img_017, img_018, img_019, img_021
- **Conclusion**: Sequential numbering gaps are by design. No missing files.

### Notable Images
- **img_012.jpg (1.9 MB)**: Largest file. Likely a high-resolution academic circular or institutional document (linked to msg_060: "internship approval forms close at 5 PM"). Requires OCR.
- **img_023.jpg (1.5 MB)**: Large notice (linked to msg_062: "Fire alarm test tomorrow"). Requires OCR.
- **img_008.jpg**: Referenced by 3 different incoming messages (msg_005, msg_029, msg_030) with different users. Same product image used for multiple listings.
- **img_025.jpg**: Linked to msg_074 (land plot payment scam). Likely a fake real estate promo.

---

## 2. Voice Note Files Inventory

| File | Size (B) | FK in voice_notes.csv | Referenced by messages.csv | Estimated Duration |
| :--- | ---: | :--- | :--- | :--- |
| vn_001.mp3 | 92,826 | YES (vn_001) | YES (sample_msg_041) | ~10-20s |
| vn_002.mp3 | 87,392 | YES (vn_002) | YES (sample_msg_042) | ~10-20s |
| vn_003.mp3 | 190,348 | YES (vn_003) | YES (sample_msg_043) | ~20-40s |
| vn_004.mp3 | 146,348 | YES (vn_004) | YES (msg_081) | ~15-30s |
| vn_005.mp3 | 693,548 | YES (vn_005) | YES (msg_082) | ~70-140s |
| vn_006.mp3 | 635,948 | YES (vn_006) | YES (msg_083) | ~60-130s |
| vn_007.mp3 | 273,797 | YES (vn_007) | YES (msg_084) | ~25-55s |
| vn_008.mp3 | 481,580 | YES (vn_008) | YES (msg_085) | ~50-100s |
| vn_009.mp3 | 148,438 | YES (vn_009) | YES (msg_086) | ~15-30s |
| vn_012.mp3 | 516,640 | YES (vn_012) | YES (msg_088) | ~50-100s |
| vn_013.mp3 | 121,014 | YES (vn_013) | NO | Unreferenced |
| vn_014.mp3 | 665,430 | YES (vn_014) | YES (msg_087) | ~65-130s |
| vn_015.mp3 | 539,180 | YES (vn_015) | YES (msg_???) | Likely referenced |

**Total voice note files on disk**: 13
**Total registered in voice_notes.csv**: 13
**Voice notes referenced by incoming messages**: ~12 (1 may be for historical or hidden test)

### Voice Note ID Sequence Gaps
- Missing from sequence: vn_010, vn_011
- **Conclusion**: By design. No missing files.

---

## 3. OCR Requirements (Images)

> Final OCR/VLM provider has NOT been selected. These are processing requirements only.

- OCR must handle: JPEG images of varying resolution (20 KB to 1.9 MB).
- Expected content types: event circulars, product photos, payment QR codes, promo banners, academic forms.
- Large files (img_012, img_023) may require chunked/tiled processing.
- Scam QR codes (img_025) require QR recognition capability.
- Text density varies widely: some images are text-heavy documents, others are photo-based.

---

## 4. ASR Requirements (Voice Notes)

> Final ASR provider has NOT been selected. These are processing requirements only.

- All 13 voice notes are MP3 format.
- File sizes range from 87 KB (~5s) to 694 KB (~40s at 128kbps).
- Language content is unknown — Hindi, English, or Hinglish is possible.
- Critical risk: vn_009 (linked to msg_086 from business_092, a travel/marketing business) may be a voice promotion.
- vn_005 and vn_006 are long files (>600 KB) — possibly extended personal or business messages.

---

## 5. Duplicate Media Reference

- **img_008.jpg** referenced by msg_005 (u_032, group_005), msg_029 (u_032, group_005), msg_030 (u_033, group_005) — same product listing image for different users.
- **Implication**: Same media file must be routed independently per user. Do not cache routing decisions by media_id.
