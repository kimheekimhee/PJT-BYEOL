from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import (
    require_POST,
    require_safe,
    require_http_methods,
)
from django.db.models import Prefetch, Q
from datetime import date, datetime, timedelta, timezone
from .models import Article, Review, Comment
from .forms import ArticleForm, ReviewForm, CommentForm, ReplyForm
from django.core.paginator import Paginator

# Create your views here.
@require_safe
def index(request):
    articles = Article.objects.order_by("-pk")
    context = {
        "articles": articles,
    }
    return render(request, "cafes/index.html", context)


@require_safe
def category(request, article_category):
    articles = Article.objects.filter(cafeType=article_category).order_by("-pk")
    context = {
        "articles": articles,
    }
    return render(request, "cafes/category.html", context)


@require_safe
def cafe_detail(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)
    cookie_value = request.COOKIES.get("hits", "_")

    if f"_{article_pk}_" not in cookie_value:  # 쿠키에 없으면
        article.hits += 1  # 조회수 증가
        article.save()

    context = {
        "article": article,
        "reviews": Review.objects.prefetch_related(
            Prefetch(
                "comment_set",
                queryset=Comment.objects.select_related("user").filter(parent=None),
                to_attr="root_comments",
            )
        ).filter(cafe=article),
        "comment_form": CommentForm(),
        "reply_form": ReplyForm(),
    }
    response = render(request, "cafes/cafe_detail.html", context)

    # https://arotein.tistory.com/40 쿠키를 이용하여 조회수 기능 만들기
    if f"_{article_pk}_" not in cookie_value:
        cookie_value += f"_{article_pk}_"
        expire_date, now = datetime.now(), datetime.now()
        expire_date += timedelta(days=1)
        expire_date = expire_date.replace(hour=0, minute=0, second=0, microsecond=0)
        expire_date -= now
        max_age = expire_date.total_seconds()
        response.set_cookie("hits", value=cookie_value, max_age=max_age, httponly=True)

    return response


@login_required
@require_http_methods(["GET", "POST"])
def cafe_create(request):
    article = None
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.user = request.user
            article.save()
            messages.success(request, "카페 작성이 완료되었습니다.")
            return redirect("cafes:cafe_detail", article.pk)
    else:
        form = ArticleForm()
    context = {
        "article": article,
        "form": form,
    }
    return render(request, "cafes/article_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def cafe_update(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)
    if request.user != article.user:
        messages.warning(request, "카페 작성자만 수정이 가능합니다.")
        return redirect("cafes:cafe_detail", article_pk)

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            article.is_updated = True
            article.save()
            messages.success(request, "카페 수정이 완료되었습니다.")
            return redirect("cafes:cafe_detail", article_pk)
    else:
        form = ArticleForm(instance=article)
    context = {
        "article": article,
        "form": form,
    }
    return render(request, "cafes/article_form.html", context)


@require_POST
def cafe_delete(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if request.user != article.user:
        messages.warning(request, "카페 작성자만 삭제 가능합니다.")
        return redirect("cafes:cafe_detail", article_pk)

    article.delete()
    messages.success(request, "성공적으로 삭제되었습니다.")
    return redirect("cafes:index")


@require_POST
def cafe_like(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if article.like_users.filter(pk=request.user.pk).exists():
        article.like_users.remove(request.user)
    else:
        article.like_users.add(request.user)
    return redirect("cafes:cafe_detail", article_pk)


@require_POST
def cafe_bookmark(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if article.bookmark_users.filter(pk=request.user.pk).exists():
        article.bookmark_users.remove(request.user)
    else:
        article.bookmark_users.add(request.user)
    return redirect("cafes:cafe_detail", article_pk)


@require_safe
def cafe_search(request):
    articles = None
    query = None
    page_obj = None

    if "q" in request.GET:
        query = request.GET.get("q")
        articles = Article.objects.order_by("-pk").filter(
            Q(name__contains=query)
            | Q(address__contains=query)
            | Q(menu__contains=query)
        )

        page = request.GET.get("page", "1")
        paginator = Paginator(articles, 6)
        page_obj = paginator.get_page(page)

    context = {
        "articles": articles,
        "query": query,
        "page_obj": page_obj,
    }
    return render(request, "cafes/cafe_search.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def review_create(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)
    review = None

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.cafe = article
            review.save()
            messages.success(request, "리뷰 작성이 완료되었습니다.")
            return redirect("cafes:cafe_detail", article_pk)
    else:
        form = ReviewForm()
    context = {
        "article": article,
        "review": review,
        "form": form,
    }
    return render(request, "cafes/review_form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def review_update(request, article_pk, review_pk):
    article = get_object_or_404(Article, pk=article_pk)
    review = get_object_or_404(Review, pk=review_pk)

    if request.user != review.user:
        messages.warning(request, "리뷰 작성자만 수정이 가능합니다.")
        return redirect("cafes:cafe_detail", article_pk)

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.is_updated = True
            review.save()
            messages.success(request, "리뷰 수정이 완료되었습니다.")
            return redirect("cafes:cafe_detail", article_pk)
    else:
        form = ReviewForm(instance=review)
    context = {
        "article": article,
        "review": review,
        "form": form,
    }
    return render(request, "cafes/review_form.html", context)


@require_POST
def review_delete(request, article_pk, review_pk):
    review = get_object_or_404(Review, pk=review_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if request.user != review.user:
        messages.warning(request, "리뷰 작성자만 삭제 가능합니다.")
    else:
        review.delete()
        messages.success(request, "성공적으로 삭제되었습니다.")
    return redirect("cafes:cafe_detail", article_pk)


@require_POST
def review_like(request, article_pk, review_pk):
    review = get_object_or_404(Review, pk=review_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if review.like_users.filter(pk=request.user.pk).exists():
        review.like_users.remove(request.user)
    else:
        review.like_users.add(request.user)
    return redirect("cafes:cafe_detail", article_pk)


@require_POST
def comment_create(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.review = review
        comment.save()
        messages.success(request, "댓글 작성이 완료되었습니다.")
    else:
        messages.warning(request, "양식이 유효하지 않습니다.")
    return redirect("cafes:cafe_detail", review.cafe.pk)


@require_POST
def comment_update(request, review_pk, comment_pk):
    review = get_object_or_404(Review, pk=review_pk)
    comment = get_object_or_404(Comment, pk=comment_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if request.user != comment.user:
        messages.warning(request, "댓글 작성자만 수정이 가능합니다.")
        return redirect("cafes:cafe_detail", review.cafe.pk)

    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        form.save()
        messages.success(request, "댓글 수정이 완료되었습니다.")
    else:
        messages.warning(request, "양식이 유효하지 않습니다.")
    return redirect("cafes:cafe_detail", review.cafe.pk)


@require_POST
def comment_delete(request, review_pk, comment_pk):
    review = get_object_or_404(Review, pk=review_pk)
    comment = get_object_or_404(Comment, pk=comment_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if request.user != comment.user:
        messages.warning(request, "댓글 작성자만 삭제가 가능합니다.")
    else:
        comment.delete()
        messages.success(request, "성공적으로 삭제되었습니다.")
    return redirect("cafes:cafe_detail", review.cafe.pk)


@require_POST
def comment_like(request, review_pk, comment_pk):
    review = get_object_or_404(Review, pk=review_pk)
    comment = get_object_or_404(Comment, pk=comment_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    if comment.like_users.filter(pk=request.user.pk).exists():
        comment.like_users.remove(request.user)
    else:
        comment.like_users.add(request.user)
    return redirect("cafes:cafe_detail", review.cafe.pk)


@require_POST
def reply_create(request, review_pk, comment_pk):
    review = get_object_or_404(Review, pk=review_pk)
    parent_comment = get_object_or_404(Comment, pk=comment_pk)

    if not request.user.is_authenticated:
        messages.warning(request, "로그인이 필요합니다.")
        return redirect("accounts:login")

    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.user = request.user
        reply.review = review
        reply.parent = parent_comment
        reply.save()
        messages.success(request, "대댓글 작성이 완료되었습니다.")
    else:
        messages.warning(request, "양식이 유효하지 않습니다.")
    return redirect("cafes:cafe_detail", review.cafe.pk)
