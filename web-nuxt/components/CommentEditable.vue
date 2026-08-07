<template>
  <div class="comment-editable">
    <div v-if="editing" class="comment-edit-form" role="form" aria-label="Sửa bình luận">
      <textarea
        ref="editEl"
        v-model="draft"
        class="textarea comment-edit-input"
        :maxlength="COMMENT_MAX_LENGTH"
        rows="3"
        aria-label="Nội dung bình luận"
        data-comment-action="edit-input"
        @keydown.esc.prevent="cancel"
        @keydown.ctrl.enter.prevent="save"
        @keydown.meta.enter.prevent="save"
      ></textarea>
      <div class="comment-edit-actions">
        <span class="comment-edit-count">{{ draft.length }}/{{ COMMENT_MAX_LENGTH }}</span>
        <button type="button" class="btn btn-ghost btn-sm" data-comment-action="edit-cancel" @click="cancel">Huỷ</button>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          data-comment-action="edit-save"
          :disabled="saving || draft.trim().length < COMMENT_MIN_LENGTH"
          @click="save"
        >
          {{ saving ? 'Đang lưu…' : 'Lưu' }}
        </button>
      </div>
    </div>
    <p v-else class="thread-content reply-text" v-html="rendered"></p>

    <div v-if="!editing" class="comment-actions">
      <slot name="actions" />
      <button
        v-if="canEdit(comment)"
        type="button"
        class="comment-reply-btn"
        data-comment-action="edit"
        @click="startEdit"
      >Sửa</button>
      <button
        v-if="canDelete(comment)"
        type="button"
        class="comment-reply-btn comment-danger-btn"
        data-comment-action="delete"
        :disabled="deleting"
        @click="remove"
      >Xoá</button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Thân một bình luận: hiển thị nội dung, hoặc ô sửa inline khi tác giả bấm "Sửa".
 *
 * Dùng chung cho bình luận gốc và trả lời trong pages/bai-viet/[id].vue để hai
 * nhánh không lệch quyền. Nút Sửa/Xoá do useCommentActions quyết định — KHÔNG
 * tự đoán quyền ở đây.
 *
 * Huỷ sửa thì nội dung cũ còn nguyên: `draft` là bản nháp riêng, `comment.content`
 * chỉ đổi sau khi API trả 200.
 */
import type { CommentLike } from '~/composables/useCommentActions'

const props = defineProps<{
  comment: CommentLike & { content?: string; mentions?: Array<{ label?: string; id?: string; type?: string }> }
}>()

const emit = defineEmits<{
  (e: 'updated', payload: { id: string; content: string; moderation_status?: string }): void
  (e: 'deleted', id: string): void
}>()

const { canEdit, canDelete, saveComment, deleteComment } = useCommentActions()

const editing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const draft = ref('')
const editEl = ref<HTMLTextAreaElement | null>(null)

const rendered = computed(() => linkifyContent(props.comment.content || '', props.comment.mentions))

function startEdit() {
  draft.value = props.comment.content || ''
  editing.value = true
  nextTick(() => editEl.value?.focus())
}

/** Huỷ = vứt bản nháp, nội dung cũ chưa bao giờ bị đụng tới. */
function cancel() {
  editing.value = false
  draft.value = ''
}

async function save() {
  if (saving.value) return
  saving.value = true
  try {
    const updated = await saveComment(props.comment.id, draft.value)
    // Thất bại → giữ nguyên ô sửa để người dùng không mất chữ đã gõ.
    if (!updated) return
    // moderation_status đi kèm nguyên vẹn: trang cha dùng nó để biết bản sửa có
    // bị hạ xuống chờ duyệt không. Nuốt ở đây là đẩy cha về chỗ phải tự đoán.
    emit('updated', {
      id: props.comment.id,
      content: updated.content,
      moderation_status: updated.moderation_status,
    })
    editing.value = false
    draft.value = ''
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (deleting.value) return
  deleting.value = true
  try {
    const ok = await deleteComment(props.comment)
    if (ok) emit('deleted', props.comment.id)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
/* .reply-text / .comment-actions / .comment-reply-btn giữ nguyên giá trị của
   pages/bai-viet/[id].vue. Phải chép lại vì scoped CSS của trang không với tới
   phần tử BÊN TRONG component con; riêng nút "Trả lời" đi qua <slot> nên vẫn
   được trang tạo kiểu (slot compile trong scope cha). */
.reply-text { margin: var(--space-1) 0 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); color: var(--ink); }
.comment-actions { display: flex; align-items: center; gap: var(--space-3); margin-top: .35rem; flex-wrap: wrap; }
/* Khách chưa đăng nhập: không nút Trả lời, không nút Sửa/Xoá → đừng để lại
   khoảng trống. Trước đây nhánh "trả lời" không có hàng hành động nào cả. */
.comment-actions:not(:has(> *)) { display: none; }
.comment-reply-btn { font-size: var(--text-xs); font-weight: var(--weight-semibold); padding: .15rem .1rem; border: none; background: none; color: var(--muted); cursor: pointer; min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; }
.comment-reply-btn:hover { color: var(--primary-fg); }
.comment-reply-btn:disabled { opacity: .55; cursor: not-allowed; }

.comment-edit-form { display: flex; flex-direction: column; gap: var(--space-2); margin: .25rem 0 .35rem; }
.comment-edit-input { width: 100%; font-size: var(--text-sm); resize: vertical; }
.comment-edit-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.comment-edit-count { font-size: var(--text-xs); color: var(--muted); margin-right: auto; }
.comment-danger-btn:hover { color: var(--danger, #c0392b); }
</style>
